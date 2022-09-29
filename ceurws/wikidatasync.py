'''
Created on 2022-08-14

@author: wf
'''
import datetime
import os
from dataclasses import dataclass
from typing import Dict, List, Union

from spreadsheet.wikidata import Wikidata

from utils.download import Download
from lodstorage.lod import LOD
from ceurws.ceur_ws import Volume, VolumeManager, CEURWS
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
        volumeTitle = getattr(volume, "title")
        volumeNumber = getattr(volume, "number")
        dblpEntityIds = self.dbpEndpoint.getDblpIdByVolumeNumber(number=volumeNumber)
        instanceOf, description = self.getEventTypeFromTitle(volumeTitle)
        record = {
            "title": self.getEventNameFromTitle(volumeTitle),
            "label": self.getEventNameFromTitle(volumeTitle),
            "description": description,
            "instanceOf": instanceOf,
            "short name": getattr(volume, "acronym"),
            "locationWikidataId": getattr(volume, "cityWikidataId"),
            "countryWikidataId": getattr(volume, "countryWikidataId"),
            "start time": getattr(volume, "dateFrom").isoformat() if getattr(volume, "dateFrom") is not None else None,
            "end time": getattr(volume, "dateTo").isoformat() if getattr(volume, "dateTo") is not None else None
        }
        if dblpEntityIds is not None and len(dblpEntityIds) > 0:
            dblpEntityId = dblpEntityIds[0]
            record["describedAt"] = self.dbpEndpoint.toDblpUrl(dblpEntityId)
            record["language of work or name"] = "Q1860"
            record["dblpEventId"] = self.dbpEndpoint.convertEntityIdToUrlId(entityId=dblpEntityId)
        return record

    def update(self,withStore:bool=True):
        '''
        update my table from the Wikidata Proceedings SPARQL query
        '''
        if self.debug:
            print(f"Querying proceedings from {self.baseurl} ...")
        wdRecords = self.sparql.queryAsListOfDicts(self.wdQuery.query)
        primaryKey = "URN_NBN"
        withCreate = True
        withDrop = True
        entityInfo=self.sqldb.createTable(wdRecords, "Proceedings", primaryKey,withCreate, withDrop,sampleRecordCount=5000,failIfTooFew=False)
        procsByURN, duplicates = LOD.getLookup(wdRecords, 'URN_NBN')
        if withStore:
            self.sqldb.store(procsByURN.values(), entityInfo, executeMany=True, fixNone=True)
        if len(duplicates)>0:
            print(f"found {len(duplicates)} duplicates URN entries")
            if len(duplicates)<10:
                print(duplicates)
        return wdRecords

    def loadProceedingsFromCache(self):
        '''
        load the proceedings recors from the cache
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

    def addProceedingsToWikidata(self, record:dict, write:bool=True, ignoreErrors:bool=False):
        """
        Creates a wikidata entry for the given record
        
        Args:
            record(dict): the data to add
            write(bool): if True actually write
            ignoreErrors(bool): if True ignore errors
            
        """
        if write:
            self.login()
        qid,errors=self.doAddProceedingsToWikidata(record, write, ignoreErrors)
        if write:
            self.logout()
        return qid,errors

    def doAddProceedingsToWikidata(self, record:dict, write:bool=True, ignoreErrors:bool=False):
        """
        Creates a wikidata proceedings entry for the given record
        
        Args:
            record(dict): the data to add
            write(bool): if True actually write
            ignoreErrors(bool): if True ignore errors
            
        """
        # see https://docs.google.com/spreadsheets/d/1fTMUuXXq_7lJgUzwLntrg4GUQ-lmlXYhS-I1Fhwc9dQ/edit#gid=0
        wdMetadata = [
            {
                "Entity": "proceedings",
                "Column": None,
                "PropertyName": "instanceof",
                "PropertyId": "P31",
                "Value": "Q1143604",
                "Type": None,
                "Qualifier": None,
                "Lookup": None
            },
            {
                "Entity": "proceedings",
                "Column": None,
                "PropertyName": "part of the series",
                "PropertyId": "P179",
                "Value": "Q27230297",
                "Type": None,
                "Qualifier": None,
                "Lookup": None
            },
            {
                "Entity": "proceedings",
                "Column": "volume",
                "PropertyName": "volume",
                "PropertyId": "P478",
                "Type": "string",
                "Qualifier": "part of the series",
                "Lookup": ""
            },
            {
                "Entity": "proceedings",
                "Column": "short name",
                "PropertyName": "short name",
                "PropertyId": "P1813",
                "Type": "text",
                "Qualifier": None,
                "Lookup": ""
            },
            {
                "Entity": "proceedings",
                "Column": "title",
                "PropertyName": "title",
                "PropertyId": "P1476",
                "Type": "text",
                "Qualifier": None,
                "Lookup": ""
            },
            {
                "Entity": "proceedings",
                "Column": "pubDate",
                "PropertyName": "publication date",
                "PropertyId": "P577",
                "Type": "date",
                "Qualifier": None,
                "Lookup": ""
            },
            {
                "Entity": "proceedings",
                "Column": "ceurwsUrl",
                "PropertyName": "described at URL",
                "PropertyId": "P973",
                "Type": "url",
                "Qualifier": None,
                "Lookup": ""
            },
            {
                "Entity": "proceedings",
                "Column": "language of work or name",
                "PropertyName": "language of work or name",
                "PropertyId": "P407",
                "Type": "itemid",
                "Qualifier": "described at URL",
                "Lookup": ""
            },
            {
                "Entity": "proceedings",
                "Column": "fullWorkUrl",
                "PropertyName": "full work available at URL",
                "PropertyId": "P953",
                "Type": "url",
                "Qualifier": None,
                "Lookup": ""
            },
            {
                "Entity": "proceedings",
                "Column": "urn",
                "PropertyName": "URN-NBN",
                "PropertyId": "P4109",
                "Type": "extid",
                "Qualifier": None,
                "Lookup": ""
             }
        ]
        mapDict, _ = LOD.getLookup(wdMetadata, "PropertyId")
        qId, errors = self.wd.addDict(row=record, mapDict=mapDict, write=write, ignoreErrors=ignoreErrors)
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

    def addLinkBetweenProceedingsAndEvent(self,
                                          volumeNumber:int,
                                          eventItemQid: str,
                                          proceedingsWikidataId:str=None,
                                          write:bool=True,
                                          ignoreErrors:bool=False):
        """
        add the link between the wikidata proceedings item and the given event wikidata item
        Args:
            volumeNumber: ceurws volumenumber of the proceedings
            eventItemQid: wikidata Qid of the event
            proceedingsWikidataId: wikidata id of the proceedings item
            write(bool): if True actually write
            ignoreErrors(bool): if True ignore errors
        """
        proceedingsWikidataId = self.getWikidataIdByVolumeNumber(number=volumeNumber)
        if proceedingsWikidataId is None:
            return None, "Volume is not unique → Proceedings item can not be determined"
        wdMetadata =[
            {"Entity": "proceedings",
             "Column": "isProceedingsFrom",
             "PropertyName": "is proceedings from",
             "PropertyId": "P4745",
             "Type": "itemid",
             "Qualifier": None,
             "Lookup": ""}
        ]
        mapDict, _ = LOD.getLookup(wdMetadata, "PropertyId")
        record = {"isProceedingsFrom": eventItemQid}
        _, errors = self.wd.addDict(itemId=proceedingsWikidataId,
                                    row=record,
                                    mapDict=mapDict,
                                    write=write,
                                    ignoreErrors=ignoreErrors)
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
        wdMetadata =[
             {
                "Entity": entity,
                "Column": None,
                "PropertyName": "instanceof",
                "PropertyId": "P31",
                "Value": entityQid,
                "Type": None,
                "Qualifier": None,
                "Lookup": None
            },
            {
                "Entity": entity,
                "Column": "short name",
                "PropertyName": "short name",
                "PropertyId": "P1813",
                "Type": "text",
                "Qualifier": None,
                "Lookup": ""
            },
            {
                "Entity": entity,
                "Column": "describedAt",
                "PropertyName": "described at URL",
                "PropertyId": "P973",
                "Type": "url",
                "Qualifier": None,
                "Lookup": ""
            },
            {
                "Entity": entity,
                "Column": "language of work or name",
                "PropertyName": "language of work or name",
                "PropertyId": "P407",
                "Type": "itemid",
                "Qualifier": "described at URL",
                "Lookup": ""
            },
            {
                "Entity": entity,
                "Column": "title",
                "PropertyName": "title",
                "PropertyId": "P1476",
                "Type": "text",
                "Qualifier": None,
                "Lookup": ""
            },
            {
                "Entity": entity,
                "Column": "dblpEventId",
                "PropertyName": "URN-NBN",
                "PropertyId": "P10692",
                "Type": "extid",
                "Qualifier": None,
                "Lookup": ""
             },
            {
                "Entity": entity,
                "Column": "start time",
                "PropertyName": "start time",
                "PropertyId": "P580",
                "Value": entityQid,
                "Type": "date",
                "Qualifier": None,
                "Lookup": ""
            },
            {
                "Entity": entity,
                "Column": "end time",
                "PropertyName": "end time",
                "PropertyId": "P582",
                "Value": entityQid,
                "Type": "date",
                "Qualifier": None,
                "Lookup": ""
            },
            {
                "Entity": entity,
                "Column": "locationWikidataId",
                "PropertyName": "location",
                "PropertyId": "P276",
                "Type": "itemid",
                "Qualifier": None,
                "Lookup": ""
            },
            {
                "Entity": entity,
                "Column": "countryWikidataId",
                "PropertyName": "country",
                "PropertyId": "P17",
                "Type": "itemid",
                "Qualifier": None,
                "Lookup": ""
            }
        ]
        mapDict, _ = LOD.getLookup(wdMetadata, "PropertyId")
        qId, errors = self.wd.addDict(row=record, mapDict=mapDict, write=write, ignoreErrors=ignoreErrors)
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
        record = {"DBLP publication ID": dblpRecordId}
        _, errors = self.wd.addDict(
                itemId=proceedingsWikidataId,
                row=record,
                mapDict=mapDict,
                write=write,
                ignoreErrors=ignoreErrors)
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
        record = {"official website": officialWebsite, "language of work or name": "Q1860"}
        mapDict, _ = LOD.getLookup(wdMetadata, "PropertyId")
        qId, errors = self.wd.addDict(itemId=itemId, row=record, mapDict=mapDict, write=write,
                                      ignoreErrors=ignoreErrors)
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
                        id_query = f"{{OPTIONAL{{ ?person wdt:P856 <{id_value}>.}} }}"
                if id_query is not None:
                    optional_clauses.append(id_query)
        id_queries = "\nUNION\n".join(optional_clauses)
        query = f"""SELECT ?person ?personLabel
                    WHERE 
                    {{
                        {id_queries}
                        SERVICE wikibase:label {{bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
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
        qres = self.sparql.queryAsListOfDicts(query)
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
        id_selects = "\n".join([f"(group_concat({id_var}Var;separator='|') as {id_var})" for id_var in id_vars])
        id_queries = "\n".join(optional_clauses)
        query = f"""PREFIX datacite: <http://purl.org/spar/datacite/>
                    PREFIX dblp: <https://dblp.org/rdf/schema#>
                    PREFIX litre: <http://purl.org/spar/literal/>
                    SELECT DISTINCT (group_concat(?nameVar;separator='|') as ?name) 
                                    (group_concat(?homepageVar;separator='|') as ?homepage)
                                    (group_concat(?affiliationVar;separator='|') as ?affiliation)
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
                    record[key] = value.split('"|"')  # issue in qlever
        return qres


@dataclass(slots=True)
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
                query = f"""{{OPTIONAL{{ {var} wdt:{wd_prop} "{value}".}} }}  # {id_name}"""
        else:
            pass
        return query
