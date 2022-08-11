'''
Created on 2022-08-11

@author: wf
'''
from tests.basetest import Basetest
from ceurws.ceur_ws import VolumeManager
from ceurws.indexparser import IndexHtmlParser

class TestIndexHtml(Basetest):
    '''
    Test reading the index HTML
    '''
    
    def setUp(self, debug=False, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.url= 'http://ceur-ws.org'
    
    def testReadingHtml(self):
        '''
        test reading the HTML file
        '''
        debug=self.debug
        debug=True
        vm=VolumeManager()
        htmlText=vm.getIndexHtml(force=False)
        indexParser=IndexHtmlParser( htmlText) 
        lineCount=len(indexParser.lines)
        self.assertTrue(lineCount>89500)
        if debug:
            print(f"{lineCount} lines found in CEUR-WS index.html")
        indexParser.parse()