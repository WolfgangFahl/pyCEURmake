'''
Created on 2022-08-14

@author: wf
'''
import os
from typing import List

from spreadsheet.wikidata import Wikidata

from utils.download import Download
from lodstorage.lod import LOD
from ceurws.ceur_ws import VolumeManager, CEURWS
from lodstorage.sparql import SPARQL
from lodstorage.sql import SQLDB
from lodstorage.query import QueryManager,EndpointManager

class WikidataSync(object):
    '''
    synchronize with wikidata
    '''

    def __init__(self):
        '''
        Constructor
        '''
        self.prepareVolumeManager()
        self.prepareRDF()
        self.wdQuery=self.qm.queriesByName["Proceedings"]
        
    def prepareRDF(self):
        # SPARQL setup
        self.endpoints=EndpointManager.getEndpoints(lang="sparql")
        self.endpointConf=self.endpoints.get("wikidata")
        self.sparql=SPARQL(self.endpointConf.endpoint)
        path=os.path.dirname(__file__)
        qYamlFile=f"{path}/resources/queries/ceurws.yaml"
        if os.path.isfile(qYamlFile):
            self.qm=QueryManager(lang="sparql",queriesPath=qYamlFile)
        
    def prepareVolumeManager(self):
        '''
        prepare my volume manager
        '''
        self.vm=VolumeManager()
        if Download.needsDownload(CEURWS.CACHE_FILE):
            self.vm.loadFromIndexHtml(force=True)
            self.vm.store()
        else:
            self.vm.loadFromBackup()
        self.volumesByNumber, _duplicates = LOD.getLookup(self.vm.getList(), 'number')
        self.volumeList=self.vm.getList()
        self.volumeCount=len(self.volumeList)
        
    def update(self):
        wdRecords=self.sparql.queryAsListOfDicts(self.wdQuery.query)
        #wdRecordsByVolume=
        sqldb=SQLDB(CEURWS.CACHE_FILE)
        primaryKey="URN_NBN"
        withCreate=True
        withDrop=True
        sqldb.createTable(wdRecords, "Proceedings", primaryKey, withCreate, withDrop)
        return wdRecords

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

    def addProceedingToWikidata(self, record:dict):
        """
        Creates a wikidata entry for the given record
        """
        wdMetadata = [
            {"Entity": "proceedings",
             "Column": None,
             "PropertyName": "instanceof",
             "PropertyId": "P31",
             "Value": "Q1143604",
             "Type": None,
             "Qualifier": None,
             "Lookup": None
             },
            {"Entity": "proceedings",
             "Column": "title",
             "PropertyName": "title",
             "PropertyId": "P1476",
             "Type": "text",
             "Qualifier": None,
             "Lookup": ""
             },
            {"Entity": "proceedings",
             "Column": "short name",
             "PropertyName": "short name",
             "PropertyId": "P1813",
             "Type": "text",
             "Qualifier": None,
             "Lookup": ""
             },
            {"Entity": "proceedings",
             "Column": None,
             "PropertyName": "part of the series",
             "PropertyId": "P179",
             "Value": "Q27230297",
             "Type": None,
             "Qualifier": None,
             "Lookup": None
             },
            {"Entity": "proceedings",
             "Column": "volume",
             "PropertyName": "volume",
             "PropertyId": "P478",
             "Type": None,
             "Qualifier": "part of the series",
             "Lookup": ""
             },
            {"Entity": "proceedings",
             "Column": "pubDate",
             "PropertyName": "publication date",
             "PropertyId": "P577",
             "Type": "date",
             "Qualifier": None,
             "Lookup": ""
             },
            {"Entity": "proceedings",
             "Column": "ceurwsUrl",
             "PropertyName": "described at URL",
             "PropertyId": "P973",
             "Type": "url",
             "Qualifier": None,
             "Lookup": ""
             },
            {"Entity": "proceedings",
             "Column": "fullWorkUrl",
             "PropertyName": "full work available at URL",
             "PropertyId": "P953",
             "Type": "url",
             "Qualifier": None,
             "Lookup": ""
             },
            {"Entity": "proceedings",
             "Column": "urn",
             "PropertyName": "URN-NBN",
             "PropertyId": "P4109",
             "Type": "extid",
             "Qualifier": None,
             "Lookup": ""
             }
        ]
        mapDict, _ = LOD.getLookup(wdMetadata, "PropertyId")
        wd = Wikidata(baseurl="https://www.wikidata.org")
        wd.loginWithCredentials()
        qId, errors = wd.addDict(row=record, mapDict=mapDict, write=True)
        wd.logout()
        return qId, errors
