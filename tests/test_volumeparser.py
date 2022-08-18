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
        self.volumeParser=VolumeParser(self.url,showHtml=False)
        self.vm=VolumeManager()
        self.vm.load()
        self.volumeList=self.vm.getList()
        self.volumesByNumber, _duplicates = LOD.getLookup(self.volumeList, 'number')
        
    def testVolumeParser(self):
        '''
        test the volumeparser
        '''
        debug=self.debug
        # title >=559
        # acronym > = 901
        dolimit=self.inPublicCI()
        dolimit=True
        debug=True
        if dolimit: 
            start=745
            limit=746 
        else: 
            start=1
            limit=len(self.volumeList)+1
        for volnumber in range(start,limit):
            volumeUrl=self.volumeParser.volumeUrl(volnumber)
            scrapedDict=self.volumeParser.parse(volumeUrl)
            if debug:
                print (scrapedDict)
            
    def testLocTime(self):
        '''
        test the loctime parts and splits
        '''
        for volnumber,volume in self.volumesByNumber.items():
            parts=[]
            if hasattr(volume,"loctime") and volume.loctime is not None:
                parts=volume.loctime.split(",")
                print(f"{volnumber:4}({len(parts)}):{volume.loctime}")
            