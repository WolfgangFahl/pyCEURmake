'''
Created on 2022-08-14

@author: wf
'''
import unittest

from tests.basetest import Basetest
from ceurws.wikidatasync import WikidataSync


class TestWikidataSync(Basetest):
    '''
    Test synchronizing with Wikidata
    '''
    
    def setUp(self, debug=False, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.wdSync=WikidataSync()

    def testWikidataSync(self):
        '''
        test synchronizing with wikidata
        '''
        wdRecords=self.wdSync.update()
        debug=True
        if debug:
            print(f"found {len(wdRecords)} wikidata records")
            
    def testGetProceedingsForVolume(self):
        '''
        get the Proceedings Record for the given volume
        '''
        self.wdSync.update()  # to create Proceedings Table
        volnumbers=[50,457]
        for volnumber in volnumbers:
            wdProc=self.wdSync.getProceedingsForVolume(volnumber)
            print(wdProc)
            
    def testVolumeListRefresh(self):
        '''
        https://github.com/WolfgangFahl/pyCEURmake/issues/19
        '''
        volumesByNumber,addedVolumeNumberList=self.wdSync.getRecentlyAddedVolumeList()
        debug=self.debug
        debug=True
        if debug:
            print(f"{len(addedVolumeNumberList)} new volumes:{addedVolumeNumberList}")
        self.assertTrue(isinstance(addedVolumeNumberList,list))
        self.assertTrue(isinstance(volumesByNumber,dict))

    @unittest.skipIf(Basetest.inPublicCI(), "queries unreliable wikidata endpoint")
    def test_getProceedingWdItemsByUrn(self):
        """tests getProceedingWdItemsByUrn"""
        test_params = [
            ("urn:nbn:de:0074-3185-4", ["http://www.wikidata.org/entity/Q113519123"]),
            ("urn:nbn:de:0074-3184-1", ["http://www.wikidata.org/entity/Q113512180"]),
            ("urn:nbn:incorrectId", [])
        ]
        wdSync = WikidataSync()
        for param in test_params:
            with self.subTest("test selection of wikidata items with given URN", param=param):
                urn, expected = param
                actual = wdSync.getProceedingWdItemsByUrn(urn)
                self.assertListEqual(expected, actual)

    @unittest.skipIf(Basetest.inPublicCI(), "queries unreliable wikidata endpoint")
    def test_getEventWdItemsByUrn(self):
        """tests getEventWdItemsByUrn"""
        test_params = [
            ("urn:nbn:de:0074-3185-4", ["http://www.wikidata.org/entity/Q113519127"]),
            ("urn:nbn:de:0074-3184-1", ["http://www.wikidata.org/entity/Q113512465", "http://www.wikidata.org/entity/Q113512468"]),
            ("urn:nbn:incorrectId", [])
        ]
        wdSync = WikidataSync()
        for param in test_params:
            with self.subTest("test selection of wikidata items with given URN", param=param):
                urn, expected = param
                actual = wdSync.getEventWdItemsByUrn(urn)
                self.assertListEqual(expected, actual)
