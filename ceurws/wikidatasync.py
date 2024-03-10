"""
Created on 2022-08-14

@author: wf
"""
import datetime
import os
import sys
from typing import Dict, List, Union

from lodstorage.lod import LOD
from lodstorage.query import EndpointManager, QueryManager
from lodstorage.sparql import SPARQL
from lodstorage.sql import SQLDB
from ez_wikidata.wikidata import UrlReference, Wikidata, WikidataResult
from ez_wikidata.wdproperty import PropertyMapping, WdDatatype

from ceurws.ceur_ws import CEURWS, PaperManager, Volume, VolumeManager
from ceurws.indexparser import ParserConfig
from ceurws.dblp import DblpEndpoint, DblpAuthorIdentifier

class WikidataSync(object):
    """
    synchronize with wikidata
    """

    def __init__(
        self,
        baseurl: str = "https://www.wikidata.org",
        debug: bool = False,
        dblp_endpoint_url: str = None,
    ):
        """
        Constructor

        Args:
            baseurl(str): the baseurl of the wikidata endpoint
            debug(bool): if True switch on debugging
            dblp_endpoint_url: sparql endpoint url of dblp
        """
        if dblp_endpoint_url is None:
            dblp_endpoint_url = "https://sparql.dblp.org/sparql"
        self.debug = debug
        self.prepareVolumeManager()
        self.preparePaperManager()
        self.prepareRDF()
        self.wdQuery = self.qm.queriesByName["Proceedings"]
        self.baseurl = baseurl
        self.wd = Wikidata(debug=debug)
        self.sqldb = SQLDB(CEURWS.CACHE_FILE)
        self.procRecords = None
        self.dblpEndpoint = DblpEndpoint(endpoint=dblp_endpoint_url)

    @classmethod
    def from_args(cls, args) -> "WikidataSync":
        """
        create a WikidataSync object from the given command line arguments

        Args:
            args(Namespace): the command line arguments
        """
        wd_en = args.wikidata_endpoint_name
        dblp_en = args.dblp_endpoint_name
        wd_sync = cls.from_endpoint_names(wd_en, dblp_en, debug=args.debug)
        return wd_sync

    @classmethod
    def from_endpoint_names(
        cls, wd_en: str, dblp_en: str, debug: bool = False
    ) -> "WikidataSync":
        """
        create a WikidataSync object from the given endpoint names

        Args:
            wd_en(str): wikidata endpoint name
            dblp_en(str): dblp endpoint name
        """
        endpoints = EndpointManager.getEndpoints()
        if not wd_en in endpoints:
            raise Exception(
                f"invalid wikidata endpoint name {wd_en}\nsee sparqlquery -le "
            )
        if not dblp_en in endpoints:
            raise Exception(
                f"invalid dblp endpoint name {dblp_en}\nsee sparqlquery -le "
            )
        dblp_ep = endpoints[dblp_en]
        wd_ep = endpoints[wd_en]
        wd_sync = cls(
            baseurl=wd_ep.endpoint, dblp_endpoint_url=dblp_ep.endpoint, debug=debug
        )
        wd_sync.wikidata_endpoint=wd_ep
        return wd_sync

    def login(self):
        self.wd.loginWithCredentials()

    def logout(self):
        self.wd.logout()

    def itemUrl(self, qId):
        url = f"{self.baseurl}/wiki/{qId}"
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
        self.pm = PaperManager()
        if self.pm.isCached():
            self.pm.fromStore(cacheFile=CEURWS.CACHE_FILE)
        else:
            print(
                "PaperManager not cached you might want to run ceur-ws --recreate",
                file=sys.stderr,
            )

    def prepareVolumeManager(self):
        """
        prepare my volume manager
        """
        self.vm = VolumeManager()
        self.vm.load()
        self.volumesByNumber, _duplicates = LOD.getLookup(self.vm.getList(), "number")
        self.volumeList = self.vm.getList()
        self.volumeCount = len(self.volumeList)
        self.volumeOptions = {}
        reverse_keys = sorted(self.volumesByNumber.keys(), reverse=True)
        for volume_number in reverse_keys:
            volume = self.volumesByNumber[volume_number]
            self.volumeOptions[volume.number] = f"Vol-{volume.number}:{volume.title}"

    def addVolume(self, volume: Volume):
        """
        add the given volume

        Args:
            volume(Volume): the volume to add
        """
        self.volumeList.append(volume)
        self.volumesByNumber[volume.number] = volume
        self.volumeCount += 1

    def getRecentlyAddedVolumeList(self) -> list:
        """
        get the list of volumes that have recently been added
        we do not expect deletions

        Returns:
            list[int]: list of volume numbers recently added

        """
        self.prepareVolumeManager()
        refreshVm = VolumeManager()
        parser_config=ParserConfig()
        parser_config.force_download=True
        self.vm.set_down_to_volume(parser_config)
        refreshVm.loadFromIndexHtml(parser_config=parser_config)
        refreshVolumesByNumber, _duplicates = LOD.getLookup(
            refreshVm.getList(), "number"
        )
        # https://stackoverflow.com/questions/3462143/get-difference-between-two-lists
        newVolumes = list(
            set(list(refreshVolumesByNumber.keys()))
            - set(list(self.volumesByNumber.keys()))
        )
        return refreshVolumesByNumber, newVolumes

    def storeVolumes(self):
        """
        store my volumes
        """
        self.vm.store()

    def getWikidataProceedingsRecord(self, volume):
        """
        get the wikidata Record for the given volume
        """
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
            "fullWorkUrl": getattr(volume, "url"),
        }
        if isinstance(record.get("pubDate"), datetime.datetime):
            record["pubDate"] = record["pubDate"].isoformat()
        return record

    def getWikidataEventRecord(self, volume: Volume):
        """
        get the wikidata Record for the given volume
        """
        volumeTitle = getattr(volume, "title", None)
        volumeNumber = getattr(volume, "number", None)
        dblpEntityIds = self.dblpEndpoint.getDblpIdByVolumeNumber(number=volumeNumber)
        instanceOf, description = self.getEventTypeFromTitle(volumeTitle)
        record = {
            "title": self.getEventNameFromTitle(volumeTitle),
            "label": self.getEventNameFromTitle(volumeTitle),
            "description": description,
            "instanceOf": instanceOf,
            "short name": getattr(volume, "acronym", None),
            "locationWikidataId": getattr(volume, "cityWikidataId", None),
            "countryWikidataId": getattr(volume, "countryWikidataId", None),
            "start time": getattr(volume, "dateFrom").isoformat()
            if getattr(volume, "dateFrom", None) is not None
            else None,
            "end time": getattr(volume, "dateTo").isoformat()
            if getattr(volume, "dateTo", None) is not None
            else None,
            "referenceUrl": volume.getVolumeUrl(),
        }
        if dblpEntityIds is not None and len(dblpEntityIds) > 0:
            dblpEntityId = dblpEntityIds[0]
            record["describedAt"] = self.dblpEndpoint.toDblpUrl(dblpEntityId)
            record["language of work or name"] = "Q1860"
            record["dblpEventId"] = self.dblpEndpoint.convertEntityIdToUrlId(
                entityId=dblpEntityId
            )
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
        wd_proceedings_records: List[dict] = self.sparql.queryAsListOfDicts(
            self.wdQuery.query
        )
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
            failIfTooFew=False,
        )
        procsByURN, duplicates = LOD.getLookup(wd_proceedings_records, "URN_NBN")
        if withStore:
            self.sqldb.store(
                procsByURN.values(), entityInfo, executeMany=True, fixNone=True
            )
        if self.debug:
            print(f"stored {len(procsByURN.values())} proceedings records")
        if len(duplicates) > 0:
            print(f"found {len(duplicates)} duplicates URN entries")
            if len(duplicates) < 10:
                print(duplicates)
        return wd_proceedings_records

    def loadProceedingsFromCache(self):
        """
        load the proceedings records from the cache
        """
        sqlQuery = "SELECT * from Proceedings"
        self.procRecords = self.sqldb.query(sqlQuery)
        return self.procRecords

    def getProceedingsForVolume(self, searchVolnumber: int) -> dict:
        """
        get the proceedings record for the given searchVolnumber

        Args:
            searchVolnumber(int): the number of the volume to search

        Returns:
            dict: the record for the proceedings in wikidata
        """
        if self.procRecords is None:
            self.loadProceedingsFromCache()
            self.procsByVolnumber = {}
            for procRecord in self.procRecords:
                volnumber = procRecord.get("sVolume", None)
                if volnumber is None:
                    procRecord.get("Volume", None)
                if volnumber is not None:
                    self.procsByVolnumber[int(volnumber)] = procRecord
        volProcRecord = self.procsByVolnumber.get(searchVolnumber, None)
        return volProcRecord

    def getProceedingWdItemsByUrn(self, urn: str) -> List[str]:
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

    def getEventWdItemsByUrn(self, urn: str) -> List[str]:
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

    def getEventsOfProceedings(self, itemId: str) -> List[str]:
        """
        get the item ids of the events the given proceedings ids is the proceedings from
        Args:
            itemId: Qid of the proceedings

        Returns:
            List of the events
        """
        query = f"""SELECT ?event WHERE {{ wd:{itemId} wdt:P4745 ?event.}}"""
        qres = self.sparql.queryAsListOfDicts(query)
        wdItems = [
            record.get("event")[len("http://www.wikidata.org/entity/") :]
            for record in qres
        ]
        return wdItems

    def getEventsOfProceedingsByVolnumber(
        self, volnumber: Union[int, str]
    ) -> List[str]:
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
        wdItems = [
            record.get("event")[len("http://www.wikidata.org/entity/") :]
            for record in qres
        ]
        return wdItems

    def addProceedingsToWikidata(
        self, record: dict, write: bool = True, ignoreErrors: bool = False
    ):
        """
        Creates a wikidata entry for the given record

        Args:
            record(dict): the data to add
            write(bool): if True actually write
            ignoreErrors(bool): if True ignore errors

        """
        if write:
            self.login()
        result = self.doAddProceedingsToWikidata(record, write, ignoreErrors)
        if write:
            self.logout()
        return result

    def doAddProceedingsToWikidata(
        self, 
        record: dict, 
        write: bool = True, 
        ignoreErrors: bool = False
    )->WikidataResult:
        """
        Creates a wikidata proceedings entry for the given record

        Args:
            record(dict): the data to add
            write(bool): if True actually write
            ignoreErrors(bool): if True ignore errors
        Returns:
            WikidataResult: the result of the add operation
        """
        mappings = [
            PropertyMapping(
                column="instanceof",
                propertyName="instanceof",
                propertyId="P31",
                propertyType=WdDatatype.itemid,
                value="Q1143604",
            ),
            PropertyMapping(
                column="part of the series",
                propertyName="part of the series",
                propertyId="P179",
                propertyType=WdDatatype.itemid,
                value="Q27230297",
            ),
            PropertyMapping(
                column="volume",
                propertyName="volume",
                propertyId="P478",
                propertyType=WdDatatype.string,
                qualifierOf="part of the series",
            ),  # ToDo: refactor qualifier of anchor column or property name?
            PropertyMapping(
                column="short name",
                propertyName="short name",
                propertyId="P1813",
                propertyType=WdDatatype.text,
            ),
            PropertyMapping(
                column="pubDate",
                propertyName="publication date",
                propertyId="P577",
                propertyType=WdDatatype.date,
            ),
            PropertyMapping(
                column="title",
                propertyName="title",
                propertyId="P1476",
                propertyType=WdDatatype.text,
            ),
            PropertyMapping(
                column="ceurwsUrl",
                propertyName="described at URL",
                propertyId="P973",
                propertyType=WdDatatype.url,
            ),
            PropertyMapping(
                column="language of work or name",
                propertyName="language of work or name",
                propertyId="P407",
                propertyType=WdDatatype.itemid,
                qualifierOf="ceurwsUrl",
            ),
            PropertyMapping(
                column="fullWorkUrl",
                propertyName="full work available at URL",
                propertyId="P953",
                propertyType=WdDatatype.url,
            ),
            PropertyMapping(
                column="urn",
                propertyName="URN-NBN",
                propertyId="P4109",
                propertyType=WdDatatype.extid,
            ),
        ]
        reference = UrlReference(url=record.get("ceurwsUrl"))
        result = self.wd.add_record(
            record=record,
            property_mappings=mappings,
            write=write,
            ignore_errors=ignoreErrors,
            reference=reference,
        )
        return result

    def askWikidata(self, askQuery: str) -> bool:
        try:
            qres = self.sparql.rawQuery(askQuery).convert()
            return qres.get("boolean", False)
        except Exception as ex:
            print(ex)
            return False

    def checkIfProceedingsFromExists(
        self, volumeNumber: int, eventItemQid: Union[str, None]
    ) -> bool:
        """Returns True if the is proceedings from relation already exists between the given proceedings and event"""
        eventVar = "?event"
        if eventItemQid is not None:
            eventVar = f"wd:{eventItemQid}"
        proceedingsWikidataId = self.getWikidataIdByVolumeNumber(number=volumeNumber)
        query = f"""ASK{{ wd:{proceedingsWikidataId} wdt:P4745 {eventVar}.}}"""
        proceedingExists = self.askWikidata(query)
        return proceedingExists

    def hasItemPropertyValueFor(self, item, propertyId: str):
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
        volumeNumber: int,
        eventItemQid: str,
        proceedingsWikidataId: str = None,
        write: bool = True,
        ignoreErrors: bool = False,
    )->WikidataResult:
        """
        add the link between the wikidata proceedings item and the given event wikidata item
        Args:
            volumeNumber: ceurws volume number of the proceedings
            eventItemQid: wikidata Qid of the event
            proceedingsWikidataId: wikidata id of the proceedings item
            write(bool): if True actually write
            ignoreErrors(bool): if True ignore errors
            
        Returns:
            WikidataResult: the result of the add operation
        """
        if proceedingsWikidataId is None:
            proceedingsWikidataId = self.getWikidataIdByVolumeNumber(
                number=volumeNumber
            )
        if proceedingsWikidataId is None:
            return None, "Volume is not unique → Proceedings item can not be determined"
        mappings = [
            PropertyMapping(
                column="isProceedingsFrom",
                propertyName="is proceedings from",
                propertyId="P4745",
                propertyType=WdDatatype.itemid,
            )
        ]
        volume_url = Volume.getVolumeUrlOf(volumeNumber)
        reference = UrlReference(volume_url)
        record = {"isProceedingsFrom": eventItemQid}
        result = self.wd.add_record(
            item_id=proceedingsWikidataId,
            record=record,
            property_mappings=mappings,
            write=write,
            ignore_errors=ignoreErrors,
            reference=reference,
        )
        return result

    def doAddEventToWikidata(
        self, record: dict, write: bool = True, ignoreErrors: bool = False
    ):
        """
        Creates a wikidata event entry for the given record
        Args:
            record(dict): the data to add
            write(bool): if True actually write
            ignoreErrors(bool): if True ignore errors

        Returns:
            WikidataResult: the result of the add operation
        """
        entityQid = record.get("instanceOf")
        entity = record.get("description")
        mappings = [
            PropertyMapping(
                column="instanceof",
                propertyName="instanceof",
                propertyId="P31",
                propertyType=WdDatatype.itemid,
                value=entityQid,
            ),
            PropertyMapping(
                column="short name",
                propertyName="short name",
                propertyId="P1813",
                propertyType=WdDatatype.text,
            ),
            PropertyMapping(
                column="describedAt",
                propertyName="described at URL",
                propertyId="P973",
                propertyType=WdDatatype.url,
            ),
            PropertyMapping(
                column="language of work or name",
                propertyName="language of work or name",
                propertyId="P407",
                propertyType=WdDatatype.itemid,
                qualifierOf="describedAt",
                value="Q1860",
            ),
            PropertyMapping(
                column="title",
                propertyName="title",
                propertyId="P1476",
                propertyType=WdDatatype.text,
            ),
            PropertyMapping(
                column="describedAt",
                propertyName="described at URL",
                propertyId="P973",
                propertyType=WdDatatype.url,
            ),
            PropertyMapping(
                column="dblpEventId",
                propertyName="DBLP event ID",
                propertyId="P10692",
                propertyType=WdDatatype.extid,
            ),
            PropertyMapping(
                column="start time",
                propertyName="start time",
                propertyId="P580",
                propertyType=WdDatatype.date,
            ),
            PropertyMapping(
                column="end time",
                propertyName="end time",
                propertyId="P582",
                propertyType=WdDatatype.date,
            ),
            PropertyMapping(
                column="locationWikidataId",
                propertyName="location",
                propertyId="P276",
                propertyType=WdDatatype.itemid,
            ),
            PropertyMapping(
                column="countryWikidataId",
                propertyName="country",
                propertyId="P17",
                propertyType=WdDatatype.itemid,
            ),
        ]
        reference_url = record.pop("referenceUrl")
        reference = UrlReference(url=reference_url)
        result = self.wd.add_record(
            record=record,
            property_mappings=mappings,
            write=write,
            ignore_errors=ignoreErrors,
            reference=reference,
        )
        return result

    def addDblpPublicationId(
        self,
        volumeNumber: int,
        dblpRecordId: str = None,
        write: bool = True,
        ignoreErrors: bool = False,
    )->WikidataResult:
        """
        try to add the dblp publication id (P8978) to the proceedings record
        Args:
            volumeNumber: ceurws volumenumber of the proceedings
            dblpRecordId: dblp record id to add to the proceedings item. If None query dblp for the record id
            write: if True actually write
            ignoreErrors(bool): if True ignore errors
            
        Returns:
            WikidataResult: the result of the add operation
        """
        proceedingsWikidataId = self.getWikidataIdByVolumeNumber(number=volumeNumber)
        if proceedingsWikidataId is None:
            return False, "Proceedings item can not be determined"
        if self.hasItemPropertyValueFor(item=proceedingsWikidataId, propertyId="P8978"):
            return (
                False,
                "dblp publication id is already assigned to the proceedings item",
            )
        if dblpRecordId is None:
            dblpRecordIds = self.dblpEndpoint.getDblpIdByVolumeNumber(volumeNumber)
            if len(dblpRecordIds) == 1:
                dblpRecordId = dblpRecordIds[0]
            elif len(dblpRecordIds) > 1:
                return (
                    False,
                    f"More than one proceedings record found ({dblpRecordIds})",
                )
            else:
                return False, f"Proceedings of volume {volumeNumber} are not in dblp"
        mappings = [
            PropertyMapping(
                column="DBLP publication ID",
                propertyName="DBLP publication ID",
                propertyId="P8978",
                propertyType=WdDatatype.extid,
            )
        ]
        wdMetadata = [
            {
                "Entity": "proceedings",
                "Column": "DBLP publication ID",
                "PropertyName": "DBLP publication ID",
                "PropertyId": "P8978",
                "Type": "extid",
                "Qualifier": None,
                "Lookup": "",
            }
        ]
        mapDict, _ = LOD.getLookup(wdMetadata, "PropertyId")
        volume_url = Volume.getVolumeUrlOf(volumeNumber)
        reference = UrlReference(volume_url)
        record = {"DBLP publication ID": dblpRecordId}
        result = self.wd.add_record(
            item_id=proceedingsWikidataId,
            record=record,
            property_mappings=mappings,
            write=write,
            ignore_errors=ignoreErrors,
            reference=reference,
        )
        return result

    def addAcronymToItem(
        self,
        itemId: str,
        acronym: str,
        desc: str = None,
        label: str = None,
        write: bool = True,
        ignoreErrors: bool = False,
    ):
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
        wdMetadata = [
            {
                "Column": "short name",
                "PropertyName": "short name",
                "PropertyId": "P1813",
                "Type": "text",
                "Lookup": "",
            }
        ]
        record = {"short name": acronym, "description": desc, "label": label}
        map_dict, _ = LOD.getLookup(wdMetadata, "PropertyId")
        qId, errors = self.wd.addDict(
            itemId=itemId,
            row=record,
            mapDict=map_dict,
            write=write,
            ignoreErrors=ignoreErrors,
        )
        return qId, errors

    def addOfficialWebsiteToItem(
        self,
        itemId: str,
        officialWebsite: str,
        write: bool = True,
        ignoreErrors: bool = False,
    ):
        """
        add the official website to the given item
        Args:
            itemId: item to add the acronym to
            officialWebsite(str): officialWebsite of the item
            write(bool): if True actually write
            ignoreErrors(bool): if True ignore errors

        Returns:
            WikidataResult: the result of the add operation
        """
        mappings = [
            PropertyMapping(
                column="official website",
                propertyName="official website",
                propertyId="P856",
                propertyType=WdDatatype.url,
            ),
            PropertyMapping(
                column="language of work or name",
                propertyName="language of work or name",
                propertyId="P407",
                propertyType=WdDatatype.itemid,
            ),
        ]
        wdMetadata = [
            {
                "Column": "official website",
                "PropertyName": "official website",
                "PropertyId": "P856",
                "Type": "url",
                "Lookup": "",
            },
            {
                "Column": "language of work or name",
                "PropertyName": "language of work or name",
                "PropertyId": "P407",
                "Type": "itemid",
                "Qualifier": "official website",
                "Lookup": "",
            },
        ]
        mapDict, _ = LOD.getLookup(wdMetadata, "PropertyId")
        record = {
            "official website": officialWebsite,
            "language of work or name": "Q1860",
        }
        qId, errors = self.wd.add_record(
            item_id=itemId,
            record=record,
            property_mappings=mapDict,
            write=write,
            ignore_errors=ignoreErrors,
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

    def getWikidataIdByDblpEventId(
        self, entityId: str, volumeNumber: int = None
    ) -> List[str]:
        """
        query wikidata for the qId of items that correspond to the given dblpEventId
        Args:
            dblpEventId: id of an dblp event

        Returns:
            list of matching wikidata items
        """
        dblpEventId = self.dblpEndpoint.convertEntityIdToUrlId(entityId=entityId)
        dblpIds = [entityId, dblpEventId]
        dblpIdsStr = " ".join([f'"{dblpId}"' for dblpId in dblpIds])
        urls = " ".join(
            [
                f"<{self.dblpEndpoint.toDblpUrl(entityId)}>",
                f"<{self.dblpEndpoint.toDblpUrl(entityId, True)}>",
            ]
        )
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
        prefixes = [
            "Proceedings of the",
            "Proceedings of",
            "Joint Proceedings of the",
            "Joint Proceedings of",
            "Joint Proceedings",
            "Joint Proceeding of the",
            "Joint Proceeding of",
            "Selected Papers of the",
            "Selected Contributions of the",
            "Workshops Proceedings for the",
            "Supplementary Proceedings of the",
            "Short Paper Proceedings of",
            "Short Paper Proceedings of the",
            "Working Notes Proceedings of the",
            "Working Notes of",
            "Working Notes for",
            "Joint Workshop Proceedings of the",
            "Joint Workshop Proceedings of",
            "Workshop Proceedings from",
            "Workshop and Poster Proceedings of the",
            "Workshops Proceedings and Tutorials of the",
            "Extended Papers of the",
            "Short Papers Proceedings of the",
            "Short Papers Proceedings of",
            "Proceedings of the Selected Papers of the",
            "Proceedings of the Working Notes of",
            "Proceedings of the Doctoral Consortium Papers Presented at the",
            "Selected Contributions to the",
            "Selected and Revised Papers of",
            "Selected Papers of",
            "Up-and-Coming and Short Papers of the",
            "Academic Papers at",
            "Poster Track of the",
            "Actes de la",
            "Post-proceedings of the",
            "Late Breaking Papers of the",
            "Anais do",
            "Proceedings del",
            "Proceedings",
            "Gemeinsamer Tagungsband der",
            "Local Proceedings of the",
            "Local Proceedings and Materials of",
        ]
        postfixes = [
            "Workshop Proceedings",
            "Proceedings",
            "Conference Proceedings",
            "Workshops Proceedings",
            "Adjunct Proceedings",
            "Poster and Demo Proceedings",
            "(full papers)",
        ]
        if title is not None:
            prefixes.sort(key=lambda prefix: len(prefix), reverse=True)
            for prefix in prefixes:
                if title.lower().startswith(prefix.lower()):
                    title = title[len(prefix) :]
                    title = title.strip()
                    break
            postfixes.sort(key=lambda postfix: len(postfix), reverse=True)
            for postfix in postfixes:
                if title.lower().endswith(postfix.lower()):
                    title = title[: -len(postfix)]
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

    def doCreateEventItemAndLinkProceedings(
        self, 
        volume: Volume, 
        proceedingsWikidataId: str = None, 
        write: bool = False
    )->Dict[str,WikidataResult]:
        """
        Create event  wikidata item for given volume and link the proceedings with the event
        Args:
            volume: volume to create the event for
            proceedingsWikidataId: proceedings wikidata id of the event
            write: If True actually write

        Returns:
            proceedingsQId, eventQId, msg
        """
        results={} 
        volNumber = getattr(volume, "number")
        if proceedingsWikidataId is None and self.checkIfProceedingsFromExists(
            volNumber, eventItemQid=None
        ):
            # link between proceedings and event already exists
            proceedingsWikidataId = self.getWikidataIdByVolumeNumber(number=volNumber)
            results["Proceedings"]=WikidataResult(
                qid=proceedingsWikidataId,
                msg=f"Proceedings for Vol-{volNumber} already exists",
            )
        dblpEntityIds = self.dblpEndpoint.getDblpIdByVolumeNumber(volNumber)
        dblpEntityId=None
        msg=None
        if len(dblpEntityIds) > 1:    
            msg=f"Multiple dblpEventIds found for Vol-{volNumber}: {','.join(dblpEntityIds)}",
        elif len(dblpEntityIds) == 1:
            dblpEntityId = dblpEntityIds[0]
        else:
            dblpEntityId = None
        results["dblp"]=WikidataResult(
            qid=dblpEntityId,
            msg=msg
        )
        wdItems = self.getWikidataIdByDblpEventId(dblpEntityId, volNumber)
        msg = ""
        eventQid = None
        if len(wdItems) == 0:
            # event item does not exist → create a new one
            volume.resolveLoctime()
            eventRecord = self.getWikidataEventRecord(volume)
            event_result= self.doAddEventToWikidata(
                record=eventRecord, write=write
            )
            eventQid=event_result.qid
            results["Event"]=event_result
        elif len(wdItems) == 1:
            results["Event"]=WikidataResult(
                # the event item already exists
                qid = wdItems[0],
                msg = "Event item already exists;"
            )
        else:
            results["Event"]=WikidataResult(
                msg=f"Multiple event entries exist: {','.join(wdItems)}"
            )
        if eventQid is not None:
            # add link between Proceedings and the event item
            link_result = self.addLinkBetweenProceedingsAndEvent(
                volumeNumber=volNumber,
                eventItemQid=eventQid,
                proceedingsWikidataId=proceedingsWikidataId,
                write=write,
            )
            link_result.msg="Added Link between Proceedings and Event item;"
            results["link"]=link_result
        return results

    @classmethod
    def removeWdPrefix(cls, value: str):
        """
        removes the wikidata entity prefix
        Args:
            value: wikidata entity url
        """
        wd_prefix = "http://www.wikidata.org/entity/"
        if value is not None and isinstance(value, str):
            if value.startswith(wd_prefix):
                value = value[len("http://www.wikidata.org/entity/") :]
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
                    id_query = DblpAuthorIdentifier.getWikidataIdQueryPart(
                        id_name, id_value, "?person"
                    )
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
