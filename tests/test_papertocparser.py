'''
Created on 2023-03-22

@author: wf
'''
from tests.basetest import Basetest

from ceurws.ceur_ws import VolumeManager
from ceurws.papertocparser import PaperTocParser
from lodstorage.lod import LOD
from ceurws.volumeparser import VolumeParser
import json

class TestPaperTocParser(Basetest):
    '''
    Test parsing Volume pages
    '''
    
    def setUp(self, debug=False, profile=True):
        """
        setUp the tests
        """
        Basetest.setUp(self, debug=debug, profile=profile)
        self.url= 'http://ceur-ws.org'
        self.vm=VolumeManager()
        self.volumeParser=VolumeParser(self.url,showHtml=False)
        self.vm.load()
        self.volumeList=self.vm.getList()
        self.volumesByNumber, _duplicates = LOD.getLookup(self.volumeList, 'number')
        
    def test_vol3264(self):
        """
        tests parsing of volume 3264
        """
        vol_number = 3264
        record,soup = self.volumeParser.parse_volume(vol_number)
        debug=self.debug
        debug=True
        if debug:
            print(json.dumps(record,indent=2))
        ptp=PaperTocParser(soup,debug=debug)
        paper_records=ptp.parsePapers()
        if debug:
            print(json.dumps(paper_records,indent=2))
       
    
