'''
Created on 2022-08-14

@author: wf
'''
from tests.basetest import Basetest
from ceurws.volumeparser import VolumeParser
from ceurws.ceur_ws import VolumeManager
from lodstorage.lod import LOD

class TestVolumeParser(Basetest):
    '''
    Test parsing Volume pages
    '''
    
    def setUp(self, debug=False, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.url= 'http://ceur-ws.org'
        
        
    def testVolumeParser(self):
        '''
        test the volumeparser
        '''
        volumeParser=VolumeParser(self.url)
        vm=VolumeManager()
        vm.load()
        volumeList=vm.getList()
        volumesByNumber, _duplicates = LOD.getLookup(volumeList, 'number')
        # title >=559
        # acronym > = 901
        if self.inPublicCI(): 
            limit=785 
        else: 
            limit=len(volumeList)+1
        for volnumber in range(775,limit):
            valid,err,scrapedDict=volumeParser.parseRDFa(str(volnumber))
            print (volnumber,valid,err,scrapedDict)
            if valid:
                volume=volumesByNumber[volnumber]
                volume.loctime=scrapedDict["loctime"]
        withStore=False
        if withStore:
            vm.store()
            