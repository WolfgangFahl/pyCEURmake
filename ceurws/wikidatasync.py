'''
Created on 2022-08-14

@author: wf
'''
import os
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
        