'''
Created on 2022-08-14

@author: wf
'''
import datetime
import os
from functools import cache
from typing import List, Union

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
            "short name": getattr(volume, "acronym")
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

    def checkIfProceedingsFromExists(self, volumeNumber:int, eventItemQid: Union[str, None]) -> bool:
        """Returns True if the is proceedings from relation already exists between the given proceedings and event"""
        eventVar = "?event"
        if eventItemQid is not None:
            eventVar = f"wd:{eventItemQid}"
        proceedingsWikidataId = self.getWikidataIdByVolumeNumber(number=volumeNumber)
        query = f"""ASK{{ wd:{proceedingsWikidataId} wdt:P4745 {eventVar}.}}"""
        try:
            qres = self.sparql.rawQuery(query).convert()
            return qres.get("boolean", False)
        except Exception as ex:
            print(ex)
            return False

    def addLinkBetweenProceedingsAndEvent(self, volumeNumber:int, eventItemQid: str, write:bool=True, ignoreErrors:bool=False):
        """
        add the link between the wikidata proceedings item and the given event wikidata item
        Args:
            volumeNumber: ceurws volumenumber of the proceedings
            eventItemQid: wikidata Qid of the event
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
        _, errors = self.wd.addDict(itemId=proceedingsWikidataId, row=record, mapDict=mapDict, write=write, ignoreErrors=ignoreErrors)
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
             }
        ]
        mapDict, _ = LOD.getLookup(wdMetadata, "PropertyId")
        qId, errors = self.wd.addDict(row=record, mapDict=mapDict, write=write, ignoreErrors=ignoreErrors)
        return qId, errors


    @cache
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
            qIds = [record.get("qid")[len("http://www.wikidata.org/entity/"):] for record in qres]
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
                    "Joint Workshop Proceedings of the", "Joint Workshop Proceedings of", "Workshop on",
                    "International Workshop on ", "Workshop Proceedings from", "Workshop and Poster Proceedings of the",
                    "Workshops Proceedings and Tutorials of the", "Extended Papers of the International Symposium on",
                    "Short Papers Proceedings of the", "Short Papers Proceedings of",
                    "Proceedings of the Selected Papers of the", "Proceedings of the Working Notes of",
                    "Proceedings of the Doctoral Consortium Papers Presented at the"]
        postfixes = ["Workshop Proceedings", "Proceedings", "Conference Proceedings", "Workshops Proceedings",
                     "Adjunct Proceedings", "Poster and Demo Proceedings"]
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
        if "conference" in title.lower():
            return academicConference
        elif "Symposium" in title.lower():
            return academicConference
        else:
            return academicWorkshop



class DblpEndpoint:
    """
    provides queries and a dblp endpoint to execute them
    """

    DBLP_REC_PREFIX = "https://dblp.org/rec/"
    DBLP_EVENT_PREFIX = "https://dblp.org/db/"

    def __init__(self, endpoint):
        self.sparql = SPARQL(endpoint)

    @cache
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

    @cache
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