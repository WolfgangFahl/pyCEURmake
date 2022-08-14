'''
Created on 2022-08-14

@author: wf
'''
from tests.basetest import Basetest
from ceurws.volumeparser import VolumeParser

class TestVolumeParser(Basetest):
    '''
    Test parsing Volume pages
    '''
    
    def setUp(self, debug=False, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.url= 'http://ceur-ws.org'
        
        
    def testVolumeParser(self):
        volumeParser=VolumeParser(self.url)
        for volnumber in ["2635"]:
            valid,err,scrapedDict=volumeParser.parse(volnumber)
            print (valid,err,scrapedDict)
            