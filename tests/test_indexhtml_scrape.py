'''
Created on 2022-08-11

@author: wf
'''
from tests.basetest import Basetest
from ceurws.ceur_ws import VolumeManager
from ceurws.indexparser import IndexHtmlParser
import logging

class TestIndexHtml(Basetest):
    '''
    Test reading the index HTML
    '''
    
    def setUp(self, debug=False, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.url= 'http://ceur-ws.org'
        
    def checkVolumes(self,volumes):
        volumeCount=len(volumes)
        print(f"{volumeCount} volumes found")
        for index,volume in enumerate(volumes.values()):
            volumeNumber=volume["number"]
            expectedVolumeNumber=volumeCount-index
            print (f'{expectedVolumeNumber:4}:{volumeNumber:4} {expectedVolumeNumber-volumeNumber}')
    
    def testReadingHtml(self):
        '''
        test reading the HTML file
        '''
        debug=self.debug
        debug=True
        if debug:
            logging.basicConfig(level=logging.DEBUG)
        vm=VolumeManager()
        htmlText=vm.getIndexHtml(force=False)
        indexParser=IndexHtmlParser(htmlText,debug=debug) 
        lineCount=len(indexParser.lines)
        self.assertTrue(lineCount>89500)
        if debug:
            print(f"{lineCount} lines found in CEUR-WS index.html")
        #limit=10
        # volumes=indexParser.parse(limit=10,verbose=True)
        volumes=indexParser.parse()
        #self.checkVolumes(volumes)
       