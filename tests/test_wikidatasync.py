'''
Created on 2022-08-14

@author: wf
'''
from tests.basetest import Basetest
from ceurws.wikidatasync import WikidataSync

class TestWikidataSync(Basetest):
    '''
    Test synchronizing with Wikidata
    '''
    
    def setUp(self, debug=False, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        
        
    def testWikidataSync(self):
        '''
        test synchronizing with wikidata
        '''
        wdSync=WikidataSync()
        wdRecords=wdSync.update()
        debug=True
        if debug:
            print(f"found {len(wdRecords)} wikidata records")
        