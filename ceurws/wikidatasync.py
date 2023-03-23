'''
Created on 2022-08-14

@author: wf
'''
import datetime
import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Union
from urllib.error import HTTPError

from spreadsheet.wikidata import PropertyMapping, UrlReference, WdDatatype, Wikidata

from ceurws.utils.download import Download
from lodstorage.lod import LOD
from ceurws.ceur_ws import Volume, VolumeManager, CEURWS, PaperManager
from lodstorage.sparql import SPARQL
from lodstorage.sql import SQLDB
from lodstorage.query import QueryManager, EndpointManager


class WikidataSync(object):
    '''
    synchronize with wikidata
    '''

    def __init__(self, baseurl="https://www.wikidata.org", debug:bool=False):
        '''
        Constructor
        
        Args:
            baseurl(str): the baseurl of the wikidata endpoint
            debug(bool): if True switch on debugging
        '''
        self.debug = debug
        self.prepareVolumeManager()
        self.preparePaperManager()
        self.prepareRDF()
        self.wdQuery = self.qm.queriesByName["Proceedings"]
        self.baseurl=baseurl
        self.wd = Wikidata(baseurl=self.baseurl, debug=debug)
        self.sqldb = SQLDB(CEURWS.CACHE_FILE)
        self.procRecords=None
        self.dbpEndpoint = DblpEndpoint(endpoint="https://qlever.cs.uni-freiburg.de/api/dblp/query")

    def login(self):
        # @FIXME add username/password handling (see gsimport)
        self.wd.loginWithCredentials()

    def logout(self):
        self.wd.logout()

    def itemUrl(self,qId):
        url=f"{self.baseurl}/wiki/{qId}"
        return url

    def prepareRDF(self):
        # SPARQL setup
        self.endpoints = EndpointManager.getEndpoints(lang="sparql")
        self.endpointConf = self.endpoints.get("wikidata")
        self.sparql = SPARQL(self.endpointConf.endpoint)
        path = os.path.dirname(__file__)
        qYamlFile = f"{path}/resources/queries/ceurws.yaml"
        if os.path.isfile(qYamlFile):
            self.qm = QueryManager(lang="sparql", queriesPath=qYamlFile)
            
    def preparePaperManager(self):
        """
        prepare my paper Manager
        """
        self.pm=PaperManager()
        if self.pm.isCached():
            self.pm.fromStore(cacheFile=CEURWS.CACHE_FILE)
        else:
            print("PaperManager not cached you might want to run ceur-ws --recreate",file=sys.stderr)

    def prepareVolumeManager(self):
        '''
        prepare my volume manager
        '''
        self.vm = VolumeManager()
        if Download.needsDownload(CEURWS.CACHE_FILE):
            self.vm.loadFromIndexHtml(force=True)
            self.vm.store()
        else:
            self.vm.loadFromBackup()
        self.volumesByNumber, _duplicates = LOD.getLookup(self.vm.getList(), 'number')
        self.volumeList = self.vm.getList()
        self.volumeCount = len(self.volumeList)

    def addVolume(self,volume:Volume):
        '''
        add the given volume

        Args:
            volume(Volume): the volume to add
        '''
        self.volumeList.append(volume)
        self.volumesByNumber[volume.number]=volume
        self.volumeCount+=1

    def getRecentlyAddedVolumeList(self)->list:
        '''
        get the list of volume that have recently been added
        we do not expect deletions

        Returns:
            list[int]: list of volume numbers recently added

        '''
        self.prepareVolumeManager()
        refreshVm=VolumeManager()
        refreshVm.loadFromIndexHtml(force=True)
        refreshVolumesByNumber, _duplicates = LOD.getLookup(refreshVm.getList(), 'number')
        # https://stackoverflow.com/questions/3462143/get-difference-between-two-lists
        newVolumes=list(
            set(list(refreshVolumesByNumber.keys()))-
            set(list(self.volumesByNumber.keys()))
        )
        return refreshVolumesByNumber,newVolumes

    def storeVolumes(self):
        """
        store my volumes
        """
        self.vm.store()

    def getWikidataProceedingsRecord(self, volume):
        '''
        get the wikidata Record for the given volume
        '''
        record = {
            "title": getattr(volume, "title"),
            "label": getattr(volume, "title"),
            "description": f"Proceedings of {getattr(volume, 'acronym')} workshop",
            "urn": getattr(volume, "urn"),
            "short name": getattr(volume, "acronym"),
            "volume": getattr(volume, "number"),
            "pubDate": getattr(volume, "pubDate"),
            "ceurwsUrl": getattr(volume, "url"),
            "language of work or name": "Q1860",
            "fullWorkUrl": getattr(volume, "url")
        }
        if isinstance(record.get("pubDate"), datetime.datetime):
            record["pubDate"] = record["pubDate"].isoformat()
        return record

    def getWikidataEventRecord(self, volume: Volume):
        '''
        get the wikidata Record for the given volume
        '''
        volumeTitle = getattr(volume, "title", None)
        volumeNumber = getattr(volume, "number", None)
        dblpEntityIds = self.dbpEndpoint.getDblpIdByVolumeNumber(number=volumeNumber)
        instanceOf, description = self.getEventTypeFromTitle(volumeTitle)
        record = {
            "title": self.getEventNameFromTitle(volumeTitle),
            "label": self.getEventNameFromTitle(volumeTitle),
            "description": description,
            "instanceOf": instanceOf,
            "short name": getattr(volume, "acronym", None),
            "locationWikidataId": getattr(volume, "cityWikidataId", None),
            "countryWikidataId": getattr(volume, "countryWikidataId", None),
            "start time": getattr(volume, "dateFrom").isoformat() if getattr(volume, "dateFrom", None) is not None else None,
            "end time": getattr(volume, "dateTo").isoformat() if getattr(volume, "dateTo", None) is not None else None,
            "referenceUrl": volume.getVolumeUrl()
        }
        if dblpEntityIds is not None and len(dblpEntityIds) > 0:
            dblpEntityId = dblpEntityIds[0]
            record["describedAt"] = self.dbpEndpoint.toDblpUrl(dblpEntityId)
            record["language of work or name"] = "Q1860"
            record["dblpEventId"] = self.dbpEndpoint.convertEntityIdToUrlId(entityId=dblpEntityId)
        if volume.isVirtualEvent():
            record["instanceOf"] = [instanceOf, "Q7935096"]
        return record

    def update(self, withStore: bool = True):
        """
        update my table from the Wikidata Proceedings SPARQL query
        """
        if self.debug:
            print(f"Querying proceedings from {self.baseurl} ...")
        # query proceedings
        wd_proceedings_records: List[dict] = self.sparql.queryAsListOfDicts(self.wdQuery.query)
        # query events
        event_query = self.qm.queriesByName["EventsByProceeding"]
        wd_event_records: List[dict] = self.sparql.queryAsListOfDicts(event_query.query)
        # add events to proceeding records
        proceedings_event_map, _duplicates = LOD.getLookup(wd_event_records, "item")
        for proceedings_record in wd_proceedings_records:
            item = proceedings_record.get("item")
            if item in proceedings_event_map:
                event_record = proceedings_event_map.get(item)
                proceedings_record.update(**event_record)
        primaryKey = "URN_NBN"
        withCreate = True
        withDrop = True
        entityInfo = self.sqldb.createTable(
                wd_proceedings_records,
                "Proceedings",
                primaryKey,
                withCreate,
                withDrop,
                sampleRecordCount=5000,
                failIfTooFew=False
        )
        procsByURN, duplicates = LOD.getLookup(wd_proceedings_records, 'URN_NBN')
        if withStore:
            self.sqldb.store(procsByURN.values(), entityInfo, executeMany=True, fixNone=True)
        if self.debug:
            print(f"stored {len(procsByURN.values())} proceedings records")
        if len(duplicates)>0:
            print(f"found {len(duplicates)} duplicates URN entries")
            if len(duplicates)<10:
                print(duplicates)
        return wd_proceedings_records

    def loadProceedingsFromCache(self):
        '''
        load the proceedings records from the cache
        '''
        sqlQuery="SELECT * from Proceedings"
        self.procRecords=self.sqldb.query(sqlQuery)
        return self.procRecords

    def getProceedingsForVolume(self,searchVolnumber:int)->dict:
        '''
        get the proceedings record for the given searchVolnumber
        
        Args:
            searchVolnumber(int): the number of the volume to search
            
        Returns:
            dict: the record for the proceedings in wikidata
        '''
        if self.procRecords is None:
            self.loadProceedingsFromCache()
            self.procsByVolnumber={}
            for procRecord in self.procRecords:
                volnumber=procRecord.get("sVolume",None)
                if volnumber is None:
                    procRecord.get("Volume",None)
                if volnumber is not None:
                    self.procsByVolnumber[int(volnumber)]=procRecord
        volProcRecord=self.procsByVolnumber.get(searchVolnumber,None)
        return volProcRecord

    def getProceedingWdItemsByUrn(self, urn:str) -> List[str]:
        """
        queries the wikidata items that have the given urn for the property P4109
        Args:
            urn: URN id to query for

        Returns:
            List of corresponding wikidata item ids or empty list of no matching item is found
        """
        query = f"""SELECT ?proceeding WHERE{{ ?proceeding wdt:P4109 "{urn}"}}"""
        qres = self.sparql.queryAsListOfDicts(query)
        wdItems = [record.get("proceeding") for record in qres]
        return wdItems

    def getEventWdItemsByUrn(self, urn:str) -> List[str]:
        """
        queries the wikidata proceedings that have the given urn assigned to P4109 and returns the assigned event
        Args:
            urn: URN id to query for

        Returns:
            List of corresponding wikidata item ids or empty list of no matching item is found
        """
        query = f"""SELECT ?event WHERE{{ ?proceeding wdt:P4109 "{urn}"; wdt:P4745 ?event .}}"""
        qres = self.sparql.queryAsListOfDicts(query)
        wdItems = [record.get("event") for record in qres]
        return wdItems

    def getEventsOfProceedings(self, itemId:str) -> List[str]:
        """
        get the item ids of the events the given proceedings ids is the proceedings from
        Args:
            itemId: Qid of the proceedings

        Returns:
            List of the events
        """
        query = f"""SELECT ?event WHERE {{ wd:{itemId} wdt:P4745 ?event.}}"""
        qres = self.sparql.queryAsListOfDicts(query)
        wdItems = [record.get("event")[len("http://www.wikidata.org/entity/"):] for record in qres]
        return wdItems

    def getEventsOfProceedingsByVolnumber(self, volnumber: Union[int, str]) -> List[str]:
        """
        get the item ids of the events the given proceedings ids is the proceedings from
        Args:
            volnumber: Volume number of the proceedings

        Returns:
            List of the events
        """
        query = f"""SELECT ?event 
                    WHERE {{
                    ?proceeding wdt:P31 wd:Q1143604; 
                                p:P179 [ps:P179 wd:Q27230297; pq:P478 "{volnumber}"]; 
                                wdt:P4745 ?event.}}
        """
        qres = self.sparql.queryAsListOfDicts(query)
        wdItems = [record.get("event")[len("http://www.wikidata.org/entity/"):] for record in qres]
        return wdItems

    def addProceedingsToWikidata(self, record: dict, write: bool = True, ignoreErrors: bool = False):
        """
        Creates a wikidata entry for the given record
        
        Args:
            record(dict): the data to add
            write(bool): if True actually write
            ignoreErrors(bool): if True ignore errors
            
        """
        if write:
            self.login()
        qid, errors = self.doAddProceedingsToWikidata(record, write, ignoreErrors)
        if write:
            self.logout()
        return qid, errors

    def doAddProceedingsToWikidata(self, record: dict, write: bool = True, ignoreErrors: bool = False):
        """
        Creates a wikidata proceedings entry for the given record
        
        Args:
            record(dict): the data to add
            write(bool): if True actually write
            ignoreErrors(bool): if True ignore errors
            
        """
        mappings = [
            PropertyMapping(column="instanceof", propertyName="instanceof", propertyId="P31", propertyType=WdDatatype.itemid, value="Q1143604"),
            PropertyMapping(column="part of the series", propertyName="part of the series", propertyId="P179", propertyType=WdDatatype.itemid, value="Q27230297"),
            PropertyMapping(column="volume", propertyName="volume", propertyId="P478", propertyType=WdDatatype.string, qualifierOf="part of the series"),  # ToDo: refactor qualifier of anchor column or property name?
            PropertyMapping(column="short name", propertyName="short name", propertyId="P1813", propertyType=WdDatatype.text),
            PropertyMapping(column="pubDate", propertyName="publication date", propertyId="P577", propertyType=WdDatatype.date),
            PropertyMapping(column="title", propertyName="title", propertyId="P1476", propertyType=WdDatatype.text),
            PropertyMapping(column="ceurwsUrl", propertyName="described at URL", propertyId="P973", propertyType=WdDatatype.url),
            PropertyMapping(column="language of work or name", propertyName="language of work or name", propertyId="P407", propertyType=WdDatatype.itemid, qualifierOf="ceurwsUrl"),
            PropertyMapping(column="fullWorkUrl", propertyName="full work available at URL", propertyId="P953", propertyType=WdDatatype.url),
            PropertyMapping(column="urn", propertyName="URN-NBN", propertyId="P4109", propertyType=WdDatatype.extid),
        ]
        reference = UrlReference(url=record.get("ceurwsUrl"))
        qId, errors = self.wd.add_record(
                record=record,
                property_mappings=mappings,
                write=write,
                ignore_errors=ignoreErrors,
                reference=reference)
        return qId, errors

    def askWikidata(self, askQuery:str) -> bool:
        try:
            qres = self.sparql.rawQuery(askQuery).convert()
            return qres.get("boolean", False)
        except Exception as ex:
            print(ex)
            return False

    def checkIfProceedingsFromExists(self, volumeNumber:int, eventItemQid: Union[str, None]) -> bool:
        """Returns True if the is proceedings from relation already exists between the given proceedings and event"""
        eventVar = "?event"
        if eventItemQid is not None:
            eventVar = f"wd:{eventItemQid}"
        proceedingsWikidataId = self.getWikidataIdByVolumeNumber(number=volumeNumber)
        query = f"""ASK{{ wd:{proceedingsWikidataId} wdt:P4745 {eventVar}.}}"""
        proceedingExists = self.askWikidata(query)
        return proceedingExists

    def hasItemPropertyValueFor(self, item, propertyId:str):
        """
        ask wikidata if the given item has a value for the given property
        Args:
            item: item Qid
            propertyId: property Pid
        Returns:
            True if the item has the property else False
        """
        query = f"""ASK{{ wd:{item} wdt:{propertyId} ?value.}}"""
        return self.askWikidata(query)

    def addLinkBetweenProceedingsAndEvent(
            self,
            volumeNumber:int,
            eventItemQid: str,
            proceedingsWikidataId:str=None,
            write:bool=True,
            ignoreErrors:bool=False):
        """
        add the link between the wikidata proceedings item and the given event wikidata item
        Args:
            volumeNumber: ceurws volume number of the proceedings
            eventItemQid: wikidata Qid of the event
            proceedingsWikidataId: wikidata id of the proceedings item
            write(bool): if True actually write
            ignoreErrors(bool): if True ignore errors
        """
        if proceedingsWikidataId is None:
            proceedingsWikidataId = self.getWikidataIdByVolumeNumber(number=volumeNumber)
        if proceedingsWikidataId is None:
            return None, "Volume is not unique → Proceedings item can not be determined"
        mappings = [
            PropertyMapping(
                    column="isProceedingsFrom",
                    propertyName="is proceedings from",
                    propertyId="P4745",
                    propertyType=WdDatatype.itemid)
        ]
        volume_url = Volume.getVolumeUrlOf(volumeNumber)
        reference = UrlReference(volume_url)
        record = {"isProceedingsFrom": eventItemQid}
        _, errors = self.wd.add_record(
                item_id=proceedingsWikidataId,
                record=record,
                property_mappings=mappings,
                write=write,
                ignore_errors=ignoreErrors,
                reference=reference
        )
        return proceedingsWikidataId, errors

    def doAddEventToWikidata(self, record: dict, write: bool = True, ignoreErrors: bool = False):
        """
        Creates a wikidata event entry for the given record
        Args:
            record(dict): the data to add
            write(bool): if True actually write
            ignoreErrors(bool): if True ignore errors

        Returns:
            (qid, errors) id of the created entry and occurred errors
        """
        entityQid = record.get("instanceOf")
        entity = record.get("description")
        mappings = [
            PropertyMapping(column="instanceof", propertyName="instanceof", propertyId="P31", propertyType=WdDatatype.itemid, value=entityQid),
            PropertyMapping(column="short name", propertyName="short name", propertyId="P1813", propertyType=WdDatatype.text),
            PropertyMapping(column="describedAt", propertyName="described at URL", propertyId="P973", propertyType=WdDatatype.url),
            PropertyMapping(column="language of work or name", propertyName="language of work or name", propertyId="P407", propertyType=WdDatatype.itemid, qualifierOf="describedAt", value="Q1860"),
            PropertyMapping(column="title", propertyName="title", propertyId="P1476", propertyType=WdDatatype.text),
            PropertyMapping(column="describedAt", propertyName="described at URL", propertyId="P973", propertyType=WdDatatype.url),
            PropertyMapping(column="dblpEventId", propertyName="DBLP event ID", propertyId="P10692", propertyType=WdDatatype.extid),
            PropertyMapping(column="start time", propertyName="start time", propertyId="P580", propertyType=WdDatatype.date),
            PropertyMapping(column="end time", propertyName="end time", propertyId="P582", propertyType=WdDatatype.date),
            PropertyMapping(column="locationWikidataId", propertyName="location", propertyId="P276", propertyType=WdDatatype.itemid),
            PropertyMapping(column="countryWikidataId", propertyName="country", propertyId="P17", propertyType=WdDatatype.itemid),

        ]
        reference_url = record.pop("referenceUrl")
        reference = UrlReference(url=reference_url)
        qId, errors = self.wd.add_record(
                record=record,
                property_mappings=mappings,
                write=write,
                ignore_errors=ignoreErrors,
                reference=reference
        )
        return qId, errors

    def addDblpPublicationId(self,
                             volumeNumber:int,
                             dblpRecordId:str=None,
                             write: bool = True,
                             ignoreErrors: bool = False):
        """
        try to add the dblp publication id (P8978) to the proceedings record
        Args:
            volumeNumber: ceurws volumenumber of the proceedings
            dblpRecordId: dblp record id to add to the proceedings item. If None query dblp for the record id
            write: if True actually write
            ignoreErrors(bool): if True ignore errors
        """
        proceedingsWikidataId = self.getWikidataIdByVolumeNumber(number=volumeNumber)
        if proceedingsWikidataId is None:
            return False, "Proceedings item can not be determined"
        if self.hasItemPropertyValueFor(item=proceedingsWikidataId, propertyId="P8978"):
            return False, "dblp publication id is already assigned to the proceedings item"
        if dblpRecordId is None:
            dblpRecordIds = self.dbpEndpoint.getDblpIdByVolumeNumber(volumeNumber)
            if len(dblpRecordIds) == 1:
                dblpRecordId = dblpRecordIds[0]
            elif len(dblpRecordIds) > 1:
                return False, f"More than one proceedings record found ({dblpRecordIds})"
            else:
                return False, f"Proceedings of volume {volumeNumber} are not in dblp"
        mappings = [PropertyMapping(column="DBLP publication ID", propertyName="DBLP publication ID", propertyId="P8978", propertyType=WdDatatype.extid)]
        wdMetadata =[
            {"Entity": "proceedings",
             "Column": "DBLP publication ID",
             "PropertyName": "DBLP publication ID",
             "PropertyId": "P8978",
             "Type": "extid",
             "Qualifier": None,
             "Lookup": ""}
        ]
        mapDict, _ = LOD.getLookup(wdMetadata, "PropertyId")
        volume_url = Volume.getVolumeUrlOf(volumeNumber)
        reference = UrlReference(volume_url)
        record = {"DBLP publication ID": dblpRecordId}
        _, errors = self.wd.add_record(
                item_id=proceedingsWikidataId,
                record=record,
                property_mappings=mappings,
                write=write,
                ignore_errors=ignoreErrors,
                reference=reference
        )
        return True, errors

    def addAcronymToItem(self, itemId: str, acronym: str, desc:str=None, label:str=None, write: bool = True, ignoreErrors: bool = False):
        """
        add the acronym to the given item
        Args:
            itemId: item to add the acronym to
            acronym(str): acronym of the item
            write(bool): if True actually write
            ignoreErrors(bool): if True ignore errors

        Returns:
            (qid, errors) id of the created entry and occurred errors
        """
        wdMetadata = [{"Column": "short name", "PropertyName": "short name", "PropertyId": "P1813", "Type": "text","Lookup": ""}]
        record = {"short name": acronym, "description": desc, "label": label}
        map_dict, _ = LOD.getLookup(wdMetadata, "PropertyId")
        qId, errors = self.wd.addDict(
                itemId=itemId,
                row=record,
                mapDict=map_dict,
                write=write,
                ignoreErrors=ignoreErrors)
        return qId, errors

    def addOfficialWebsiteToItem(self, itemId: str, officialWebsite: str, write: bool = True, ignoreErrors: bool = False):
        """
        add the official website to the given item
        Args:
            itemId: item to add the acronym to
            officialWebsite(str): officialWebsite of the item
            write(bool): if True actually write
            ignoreErrors(bool): if True ignore errors

        Returns:
            (qid, errors) id of the created entry and occurred errors
        """
        mappings = [
            PropertyMapping(column="official website", propertyName="official website", propertyId="P856", propertyType=WdDatatype.url),
            PropertyMapping(column="language of work or name", propertyName="language of work or name", propertyId="P407", propertyType=WdDatatype.itemid),
        ]
        wdMetadata = [{
                "Column": "official website",
                "PropertyName": "official website",
                "PropertyId": "P856",
                "Type": "url",
                "Lookup": ""
            },
            {
                "Column": "language of work or name",
                "PropertyName": "language of work or name",
                "PropertyId": "P407",
                "Type": "itemid",
                "Qualifier": "official website",
                "Lookup": ""
            }]
        mapDict, _ = LOD.getLookup(wdMetadata, "PropertyId")
        record = {"official website": officialWebsite, "language of work or name": "Q1860"}
        qId, errors = self.wd.add_record(
                item_id=itemId,
                record=record,
                property_mappings=mapDict,
                write=write,
                ignore_errors=ignoreErrors
        )
        return qId, errors

    def getWikidataIdByVolumeNumber(self, number) -> str:
        """
        query wikidata for the qId of the proceedings of the given volume number
        Args:
            number: volume number
        """
        query = f"""SELECT * WHERE{{ ?proceeding p:P179 [ps:P179 wd:Q27230297; pq:P478 "{number}"].}}"""
        qres = self.sparql.queryAsListOfDicts(query)
        qId = None
        if qres is not None and qres != []:
            qIds = [record.get("proceeding").split("/")[-1] for record in qres]
            if len(qIds) > 1:
                print("CEUR-WS volume number is not unique")
            else:
                qId = qIds[0]
        return qId

    def getWikidataIdByDblpEventId(self, entityId: str, volumeNumber: int=None) -> List[str]:
        """
        query wikidata for the qId of items that correspond to the given dblpEventId
        Args:
            dblpEventId: id of an dblp event

        Returns:
            list of matching wikidata items
        """
        dblpEventId = self.dbpEndpoint.convertEntityIdToUrlId(entityId=entityId)
        dblpIds = [entityId, dblpEventId]
        dblpIdsStr = " ".join([f'"{dblpId}"' for dblpId in dblpIds])
        urls = " ".join([f"<{self.dbpEndpoint.toDblpUrl(entityId)}>", f"<{self.dbpEndpoint.toDblpUrl(entityId, True)}>"])
        volumeQuery = ""
        if volumeNumber is not None:
            volumeQuery = f"""
            UNION
                  {{
                  ?proceeding p:P179 [ps:P179 wd:Q27230297; pq:P478 "{volumeNumber}"].
                  ?proceeding wdt:P4745 ?qid.
                  }}
            """
        query = f"""SELECT DISTINCT ?qid
            WHERE{{
              VALUES ?url {{ {urls} }}
              VALUES ?dblpEventId {{ {dblpIdsStr} }}
              VALUES ?eventType {{wd:Q2020153 wd:Q40444998}}
              {{?qid wdt:P31 ?eventType; wdt:P973 ?url}}
              UNION
              {{?qid wdt:P31 ?eventType; wdt:P10692 ?dblpEventId}}
              {volumeQuery}
            }}
        """
        qres = self.sparql.queryAsListOfDicts(query)
        qIds = []
        if qres is not None and qres != []:
            qIds = [self.removeWdPrefix(record.get("qid")) for record in qres]
        return qIds

    @classmethod
    def getEventNameFromTitle(cls, title: str) -> str:
        """
        Get the event name from the given proceedings title
        Args:
            title: title of the proceeding

        Returns:
            name of the event
        """
        prefixes = ["Proceedings of the", "Proceedings of", "Joint Proceedings of the", "Joint Proceedings of",
                    "Joint Proceedings", "Joint Proceeding of the", "Joint Proceeding of", "Selected Papers of the",
                    "Selected Contributions of the", "Workshops Proceedings for the",
                    "Supplementary Proceedings of the", "Short Paper Proceedings of", "Short Paper Proceedings of the",
                    "Working Notes Proceedings of the", "Working Notes of", "Working Notes for",
                    "Joint Workshop Proceedings of the", "Joint Workshop Proceedings of",
                    "Workshop Proceedings from", "Workshop and Poster Proceedings of the",
                    "Workshops Proceedings and Tutorials of the", "Extended Papers of the",
                    "Short Papers Proceedings of the", "Short Papers Proceedings of",
                    "Proceedings of the Selected Papers of the", "Proceedings of the Working Notes of",
                    "Proceedings of the Doctoral Consortium Papers Presented at the", "Selected Contributions to the",
                    "Selected and Revised Papers of", "Selected Papers of", "Up-and-Coming and Short Papers of the",
                    "Academic Papers at", "Poster Track of the", "Actes de la", "Post-proceedings of the",
                    "Late Breaking Papers of the", "Anais do", "Proceedings del", "Proceedings",
                    "Gemeinsamer Tagungsband der", "Local Proceedings of the", "Local Proceedings and Materials of"]
        postfixes = ["Workshop Proceedings", "Proceedings", "Conference Proceedings", "Workshops Proceedings",
                     "Adjunct Proceedings", "Poster and Demo Proceedings", "(full papers)"]
        if title is not None:
            prefixes.sort(key=lambda prefix: len(prefix), reverse=True)
            for prefix in prefixes:
                if title.lower().startswith(prefix.lower()):
                    title = title[len(prefix):]
                    title = title.strip()
                    break
            postfixes.sort(key=lambda postfix: len(postfix), reverse=True)
            for postfix in postfixes:
                if title.lower().endswith(postfix.lower()):
                    title = title[:-len(postfix)]
                    title = title.strip(" .,")
                    break
        return title

    @classmethod
    def getEventTypeFromTitle(cls, title: str) -> (str, str):
        """
        Extract the event type from the given title
        Assumption: lowest mentioned type is the correct one
        Args:
            title: title of the event

        Returns:
            wikidata id and label of the event type
        """
        if title is None or title == "":
            return None, None
        academicConference = ("Q2020153", "academic conference")
        academicWorkshop = ("Q40444998", "academic workshop")
        if "workshop" in title.lower():
            return academicWorkshop
        elif "conference" in title.lower():
            return academicConference
        elif "symposium" in title.lower():
            return academicConference
        else:
            return academicWorkshop

    def doCreateEventItemAndLinkProceedings(self, volume: Volume, proceedingsWikidataId:str=None, write:bool=False):
        """
        Create event  wikidata item for given volume and link the proceedings with the event
        Args:
            volume: volume to create the event for
            proceedingsWikidataId: proceedings wikidata id of the event
            write: If True actually write

        Returns:
            proceedingsQId, eventQId, msg
        """
        volNumber = getattr(volume, "number")
        if proceedingsWikidataId is None and self.checkIfProceedingsFromExists(volNumber, eventItemQid=None):
            # link between proceedings and event already exists
            proceedingsWikidataId = self.getWikidataIdByVolumeNumber(number=volNumber)
            return proceedingsWikidataId, None, "Event and Link between proceedings and event already exists"
        dblpEntityIds = self.dbpEndpoint.getDblpIdByVolumeNumber(volNumber)
        if len(dblpEntityIds) > 1:
            return None, None, f"Multiple dblpEventIds found for Vol-{volNumber}: {','.join(dblpEntityIds)}"
        elif len(dblpEntityIds) == 1:
            dblpEntityId = dblpEntityIds[0]
        else:
            dblpEntityId = None
        wdItems = self.getWikidataIdByDblpEventId(dblpEntityId, volNumber)
        msg=""
        eventQid = None
        errors = None
        if len(wdItems) == 0:
            # event item does not exist → create a new one
            volume.resolveLoctime()
            eventRecord = self.getWikidataEventRecord(volume)
            eventQid, errors = self.doAddEventToWikidata(record=eventRecord, write=write)
            msg += "Created Event item;"
        elif len(wdItems) == 1:
            # the event item already exists
            eventQid = wdItems[0]
            msg += "Event item already exists;"
        else:
            return None, None, f"Multiple event entries exist: {','.join(wdItems)}"
        if eventQid is not None:
            # add link between Proceedings and the event item
            proceedingsWikidataId, errors = self.addLinkBetweenProceedingsAndEvent(
                    volumeNumber=volNumber,
                    eventItemQid=eventQid,
                    proceedingsWikidataId=proceedingsWikidataId,
                    write=write
            )
            msg += "Added Link between Proceedings and Event item;"
            return proceedingsWikidataId, eventQid, msg

        else:
            return None, None, f"An error occured during the creation of the proceedings entry for {volume}"

    @classmethod
    def removeWdPrefix(cls, value: str):
        """
        removes the wikidata entity prefix
        Args:
            value: wikidata entity url
        """
        wd_prefix =  "http://www.wikidata.org/entity/"
        if value is not None and isinstance(value, str):
            if value.startswith(wd_prefix):
                value = value[len("http://www.wikidata.org/entity/"):]
        return value

    def getAuthorByIds(self, identifiers: dict) -> Dict[str, str]:
        """
        Based on the given identifiers get potential author items
        the names of the identifiers must be according to DblpAuthorIdentifier
        Args:
            identifiers: known identifiers of the author
        """
        if identifiers is None or len(identifiers) == 0:
            return dict()
        id_map = DblpAuthorIdentifier.getAllAsMap()
        optional_clauses = []
        for id_name, id_value in identifiers.items():
            if id_value is not None and id_value != "":
                id_query = None
                if id_name in id_map:
                    wd_prop = id_map.get(id_name).wikidata_property
                    id_query = DblpAuthorIdentifier.getWikidataIdQueryPart(id_name, id_value, "?person")
                else:
                    if id_name == "homepage":
                        id_query = f"{{ ?person wdt:P856 <{id_value}>. }}"
                if id_query is not None:
                    optional_clauses.append(id_query)
        id_queries = "\nUNION\n".join(optional_clauses)
        query = f"""SELECT DISTINCT ?person ?personLabel
                    WHERE
                    {{
                        {id_queries}
                        ?person rdfs:label ?personLabel. FILTER(lang(?personLabel)="en").
                    }}"""
        qres = self.sparql.queryAsListOfDicts(query)
        res = dict()
        for record in qres:
            if record is None or len(record) == 0:
                continue
            item_id = self.removeWdPrefix(record.get("person"))
            name = record.get("personLabel")
            res[item_id] = name
        return res


class DblpEndpoint:
    """
    provides queries and a dblp endpoint to execute them
    """

    DBLP_REC_PREFIX = "https://dblp.org/rec/"
    DBLP_EVENT_PREFIX = "https://dblp.org/db/"

    def __init__(self, endpoint):
        self.sparql = SPARQL(endpoint)

    def getDblpIdByVolumeNumber(self, number) -> List[str]:
        """
        Get the dblp entity id by given volume number
        Args:
            number: volume number
        """
        query = f"""PREFIX dblp: <https://dblp.org/rdf/schema#>
            SELECT *
            WHERE {{ 
                ?proceeding dblp:publishedIn "CEUR Workshop Proceedings";
                            dblp:publishedInSeriesVolume "{number}".
                }}
        """
        try:
            qres = self.sparql.queryAsListOfDicts(query)
        except HTTPError as ex:
            print("dblp sparql endpoint unavailable")
            qres = None
        qIds = []
        if qres is not None and qres != []:
            qIds = [record.get("proceeding")[len(self.DBLP_REC_PREFIX):] for record in qres]
        return qIds

    def getDblpUrlByDblpId(self, entityId) -> Union[str, None]:
        """
        Get the dblp url for given entity id
        Args:
            entityId: volume url
        """
        if entityId is None or entityId == "":
            return None
        entityUrl = self.DBLP_REC_PREFIX + entityId
        query = f"""PREFIX dblp: <https://dblp.org/rdf/schema#>
                SELECT *
                WHERE {{ 
                    <{entityUrl}> dblp:listedOnTocPage ?url .
                    }}
            """
        qres = self.sparql.queryAsListOfDicts(query)
        qIds = []
        if qres is not None and qres != []:
            qIds = [record.get("url")[len(self.DBLP_EVENT_PREFIX):] for record in qres]
        qId = qIds[0] if qIds is not None and len(qIds) > 0 else None
        return qId

    def convertEntityIdToUrlId(self, entityId:str) -> Union[str, None]:
        """
        Convert the given entityId to the id used in the url
        Note: use with care this conversion does not always work
        Args:
            entityId: id of the entity
        Example:
            conf/aaai/2022 → conf/aaai/aaai2022

        Returns
            str - id used in the url
            None - if the given entityId can not be converted
        """
        return self.getDblpUrlByDblpId(entityId)

    def toDblpUrl(self, entityId:str, withPostfix: bool = False) -> Union[str, None]:
        """
        Convert the given id to the corresponding dblp url
        Args:
            entityId: dblp event id
            withPostfix: If True add the postfix ".html"

        Returns:
            ddblp url of None if the url can not be generated for the given input
        """
        urlId = self.convertEntityIdToUrlId(entityId)
        if urlId is None:
            return None
        postfix = ".html"
        url = self.DBLP_EVENT_PREFIX + urlId
        if withPostfix:
            url += postfix
        return url

    def getEditorsOfVolume(self, number:Union[int, str, None]) -> List[dict]:
        """
        Get the editors for the given volume number
        Args:
            number: number of the volume if none query for all ceur-ws editors

        Returns:
            list of dictionaries where a dict represents one editor containing all identifiers of the editor
        """
        if number is None:
            number_var = "?volumeNumber"
        else:
            number_var = f'"{number}"'
        dblp_identifiers = DblpAuthorIdentifier.all()
        optional_clauses: List[str] = []
        id_vars: List[str] = []
        for identifier in dblp_identifiers:
            id_var = f"?{identifier.name}"
            optional_clauses.append(f"""OPTIONAL{{
                ?editor datacite:hasIdentifier {id_var}_blank.
                {id_var}_blank datacite:usesIdentifierScheme {identifier.dblp_property};
                litre:hasLiteralValue {id_var}Var.}}""")
            id_vars.append(id_var)
        id_selects = "\n".join([f"(group_concat(DISTINCT {id_var}Var;separator='|') as {id_var})" for id_var in id_vars])
        id_queries = "\n".join(optional_clauses)
        query = f"""PREFIX datacite: <http://purl.org/spar/datacite/>
                    PREFIX dblp: <https://dblp.org/rdf/schema#>
                    PREFIX litre: <http://purl.org/spar/literal/>
                    SELECT DISTINCT (group_concat(DISTINCT ?nameVar;separator='|') as ?name) 
                                    (group_concat(DISTINCT ?homepageVar;separator='|') as ?homepage)
                                    (group_concat(DISTINCT ?affiliationVar;separator='|') as ?affiliation)
                                    {id_selects}
                    WHERE{{
                        ?proceeding dblp:publishedIn "CEUR Workshop Proceedings";
                                    dblp:publishedInSeriesVolume {number_var};
                                    dblp:editedBy ?editor.
                        ?editor dblp:primaryCreatorName ?nameVar.
                        OPTIONAL{{?editor dblp:primaryHomepage ?homepageVar.}}
                        OPTIONAL{{?editor dblp:primaryAffiliation ?affiliationVar.}}
                        {id_queries}
                    }}
                    GROUP BY ?editor
                """
        qres = self.sparql.queryAsListOfDicts(query)
        for record in qres:
            for key, value in record.items():
                if "|" in value:
                    record[key] = value.split('"|"')  # issue in qlever see https://github.com/ad-freiburg/qlever/discussions/806
        return qres


@dataclass
class DblpAuthorIdentifier:
    """
    represents an author id available in dblp
    and the corresponding property in wikidata
    """
    name: str  # the name should be usable as SPARQL variable
    dblp_property: str
    wikidata_property: str

    @classmethod
    def all(cls) -> List['DblpAuthorIdentifier']:
        """
        returns all available identifiers
        """
        res = [
            DblpAuthorIdentifier("dblp", "datacite:dblp", "P2456"),
            DblpAuthorIdentifier("wikidata", "datacite:wikidata", None),
            DblpAuthorIdentifier("orcid", "datacite:orcid", "P496"),
            DblpAuthorIdentifier("googleScholar", "datacite:google-scholar", "P1960"),
            DblpAuthorIdentifier("acm", "datacite:acm", "P864"),
            DblpAuthorIdentifier("twitter", "datacite:twitter", "P2002"),
            DblpAuthorIdentifier("github", "datacite:github", "P2037"),
            DblpAuthorIdentifier("viaf", "datacite:viaf", "P214"),
            DblpAuthorIdentifier("scigraph", "datacite:scigraph", "P10861"),
            DblpAuthorIdentifier("zbmath", "datacite:zbmath", "P1556"),
            DblpAuthorIdentifier("researchGate", "datacite:research-gate", "P6023"),
            DblpAuthorIdentifier("mathGenealogy", "datacite:math-genealogy", "P549"),
            DblpAuthorIdentifier("loc", "datacite:loc", "P244"),
            DblpAuthorIdentifier("linkedin", "datacite:linkedin", "P6634"),
            DblpAuthorIdentifier("lattes", "datacite:lattes", "P1007"),
            DblpAuthorIdentifier("isni", "datacite:isni", "P213"),
            DblpAuthorIdentifier("ieee", "datacite:ieee", "P6479"),
            DblpAuthorIdentifier("gepris", "datacite:gepris", "P4872"),
            DblpAuthorIdentifier("gnd", "datacite:gnd", "P227"),
        ]
        return res

    @classmethod
    def getAllAsMap(cls) -> Dict[str, 'DblpAuthorIdentifier']:
        """
        return all all available identifiers as map
        """
        res = dict()
        for identifier in cls.all():
            res[identifier.name] = identifier
        return res

    @classmethod
    def getWikidataIdQueryPart(cls, id_name: str, value: str, var: str):
        """
        Generates for the given identifier the wikidata query
        Args:
            id_name: name of the identifier
            value: the identifier value
            var: name of the variable which should have the id
        """
        if not var.startswith("?"):
            var = "?" + var
        query = None
        wd_prop = cls.getAllAsMap().get(id_name).wikidata_property
        if id_name == "wikidata":
            values = value
            if isinstance(value, str):
                values = [value]
            value_urls = " ".join([f"wd:{value}" for value in values])
            query = f"""{{ SELECT * WHERE {{ VALUES ?person {{ {value_urls} }} }} }}# {id_name}"""
        elif id_name in cls.getAllAsMap():
            if isinstance(value, list):
                values = " ".join([f'"{value}"' for value in value])
                query = f"""{{OPTIONAL{{
                            VALUES ?{id_name} {{ {values} }}
                            {var} wdt:{wd_prop} ?{id_name}.}} 
                            }}  # {id_name}"""
            else:
                query = f"""{{ {var} wdt:{wd_prop} "{value}". }}  # {id_name}"""
        else:
            pass
        return query
