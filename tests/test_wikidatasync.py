'''
Created on 2022-08-14

@author: wf
'''
import unittest

from tests.basetest import Basetest
from ceurws.wikidatasync import DblpEndpoint, WikidataSync


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
            ("urn:nbn:de:0074-3185-4", ["http://www.wikidata.org/entity/Q113574688"]),
            ("urn:nbn:de:0074-3184-1", ["http://www.wikidata.org/entity/Q113512465", "http://www.wikidata.org/entity/Q113512468"]),
            ("urn:nbn:incorrectId", [])
        ]
        wdSync = WikidataSync()
        for param in test_params:
            with self.subTest("test selection of wikidata items with given URN", param=param):
                urn, expected = param
                actual = wdSync.getEventWdItemsByUrn(urn)
                self.assertListEqual(expected, actual)

    @unittest.skipIf(Basetest.inPublicCI(), "queries unreliable wikidata endpoint")
    def test_getWikidataIdByVolumeNumber(self):
        """tests getWikidataIdByVolumeNumber"""
        test_params = [
            ("1", "Q107266045"),
            ("2400", "Q113542875"),
            ("-1", None),
            (2400, "Q113542875")
        ]
        for param in test_params:
            with self.subTest("test wikidata id query by volume number", param=param):
                number, expected = param
                actual = self.wdSync.getWikidataIdByVolumeNumber(number)
                self.assertEqual(expected, actual)

    @unittest.skipIf(Basetest.inPublicCI(), "queries unreliable wikidata endpoint")
    def test_getWikidataIdByDblpEventId(self):
        """tests getWikidataIdByDblpEventId"""
        test_params = [("conf/ictcs/ictcs2019", None, []),
                       ("conf/ictcs/2019", None, ["Q106245764"]),
                       ("conf/ictcs", None, []), (None, None, []), ["", None, []],
                       ("conf/intsol/intsol2021w", 3106, ['Q113576470'])]
        for param in test_params:
            with self.subTest("test wikidata id query by volume number", param=param):
                entityId, number, expected = param
                actual = self.wdSync.getWikidataIdByDblpEventId(entityId, volumeNumber=number)
                self.assertListEqual(expected, actual)

    def test_getEventNameFromTitle(self):
        """tests getEventNameFromTitle"""
        test_params = [
            ("Proceedings of the 20th Internal Workshop on Satisfiability Modulo Theories", "20th Internal Workshop on Satisfiability Modulo Theories"),
            ("Working Notes Proceedings of the MediaEval 2021 Workshop", "MediaEval 2021 Workshop"),
            ("Proceedings of The 11th Seminary of Computer Science Research at Feminine(RIF 2022)", "11th Seminary of Computer Science Research at Feminine(RIF 2022)"),
            ('Selected Papers of the VIII International Scientific Conference “Information Technology and Implementation" (IT&I-2021). Workshop Proceedings', 'VIII International Scientific Conference “Information Technology and Implementation" (IT&I-2021)'),
            ("Joint Proceedings of Baltic DB&IS 2022 Doctoral Consortium and Forum", "Baltic DB&IS 2022 Doctoral Consortium and Forum"),
            ("Short Paper Proceedings of the First International Workshop on Agile Methods for Information Systems Engineering (Agil-ISE 2022)", "First International Workshop on Agile Methods for Information Systems Engineering (Agil-ISE 2022)"),
            ("Supplementary Proceedings of the XXIII International Conference on Data Analytics and Management in Data Intensive Domains (DAMDID/RCDL 2021)", "XXIII International Conference on Data Analytics and Management in Data Intensive Domains (DAMDID/RCDL 2021)"),
            ("Workshops Proceedings for the 29th International Conference on Case-Based Reasoning", "29th International Conference on Case-Based Reasoning"),
            ('Selected Contributions of the "Russian Advances in Artificial Intelligence" Track at RCAI 2020', '"Russian Advances in Artificial Intelligence" Track at RCAI 2020'),
            ("Working Notes of FIRE 2021 - Forum for Information Retrieval Evaluation", "FIRE 2021 - Forum for Information Retrieval Evaluation"),
            ("Working Notes for CLEF 2014 Conference", "CLEF 2014 Conference"),
            ("Joint Workshop Proceedings of the 3rd Edition of Knowledge-aware and Conversational Recommender Systems (KaRS) and the 5th Edition of Recommendation in Complex Environments (ComplexRec)", "3rd Edition of Knowledge-aware and Conversational Recommender Systems (KaRS) and the 5th Edition of Recommendation in Complex Environments (ComplexRec)"),
            ("Workshop on Linked Data on the Web", "Linked Data on the Web"),
            ("International Workshop on Enabling Service Business Ecosystems - ESBE'09", "Enabling Service Business Ecosystems - ESBE'09"),
            ("Workshop Proceedings from The Twenty-Third International Conference on Case-Based Reasoning", "The Twenty-Third International Conference on Case-Based Reasoning"),
            ("Workshop and Poster Proceedings of the 8th Joint International Semantic Technology Conference", "8th Joint International Semantic Technology Conference"),
            ("Workshops Proceedings and Tutorials of the 28th ACM Conference on Hypertext and Social Media", "28th ACM Conference on Hypertext and Social Media"),
            ("Extended Papers of the International Symposium on Digital Humanities (DH 2016)", "Digital Humanities (DH 2016)"),
            ("Short Papers Proceedings of the 2nd International Workshop on Software Engineering & Technology (Q-SET 2021)", "2nd International Workshop on Software Engineering & Technology (Q-SET 2021)"),
            ("", ""),
            (None, None),
            ('Selected Papers of the 7th International Conference "Information Technology and Interactions" (IT&I-2020). Conference Proceedings', '7th International Conference "Information Technology and Interactions" (IT&I-2020)'),
            ("SAMT 2006 1st International Conference on Semantic and Digital Media Technologies Poster and Demo Proceedings", "SAMT 2006 1st International Conference on Semantic and Digital Media Technologies"),
            ("Proceedings of the Selected Papers of the Workshop on Emerging Technology Trends on the Smart Industry and the Internet of Things (TTSIIT 2022)", "Workshop on Emerging Technology Trends on the Smart Industry and the Internet of Things (TTSIIT 2022)"),
            ("Proceedings of the Working Notes of CLEF 2022 - Conference and Labs of the Evaluation Forum", "CLEF 2022 - Conference and Labs of the Evaluation Forum"),
            ("Proceedings of the Doctoral Consortium Papers Presented at the 34th International Conference on Advanced Information Systems Engineering (CAiSE 2022)", "34th International Conference on Advanced Information Systems Engineering (CAiSE 2022)"),
            ('Selected Papers of the II International Scientific Symposium "Intelligent Solutions" (IntSol-2021). Workshop Proceedings', 'II International Scientific Symposium "Intelligent Solutions" (IntSol-2021)')
        ]
        for param in test_params:
            with self.subTest("test event name extraction", param=param):
                title, expected = param
                actual = self.wdSync.getEventNameFromTitle(title)
                self.assertEqual(expected, actual)

    def test_getEventTypeFromTitle(self):
        """tests getEventTypeFromTitle"""
        test_params = [
            ("20th Internal Workshop on Satisfiability Modulo Theories", ("Q40444998", "academic workshop")),
            ("Baltic DB&IS 2022 Doctoral Consortium and Forum", ("Q40444998", "academic workshop")),
            ("20th Italian Conference on Theoretical Computer Science", ("Q2020153", "academic conference")),
            ("", (None, None)), (None, (None, None))
        ]
        for param in test_params:
            with self.subTest("test event type extraction", param=param):
                title, (expectedQid, expectedDesc) = param
                actualQid, actualDesc = self.wdSync.getEventTypeFromTitle(title)
                self.assertEqual(expectedQid, actualQid)
                self.assertEqual(expectedDesc, actualDesc)


    @unittest.skipIf(False, "Only manual execution of the test since it edits wikidata")
    def test_addLinkBetweenProceedingsAndEvent(self):
        """tests addLinkBetweenProceedingsAndEvent"""
        volumeNumber = 1949
        eventItemQid = "Q106338689"
        self.wdSync.wd.debug=self.debug
        self.wdSync.login()
        qId, errors = self.wdSync.addLinkBetweenProceedingsAndEvent(volumeNumber=volumeNumber, eventItemQid=eventItemQid, write=True)
        self.wdSync.logout()
        print(qId)
        print(errors)

    @unittest.skipIf(Basetest.inPublicCI(), "queries unreliable wikidata endpoint")
    def test_checkIfProceedingsFromExists(self):
        """tests checkIfProceedingsFromExists"""
        with self.subTest("Test existing relation"):
            volumeNumber =  3185
            eventQid = "Q113574688"
            actual = self.wdSync.checkIfProceedingsFromExists(volumeNumber, eventQid)
            self.assertTrue(actual)
        with self.subTest("Test existing relation without giving the event"):
            volumeNumber =  3185
            eventQid = None
            actual = self.wdSync.checkIfProceedingsFromExists(volumeNumber, eventQid)
            self.assertTrue(actual)
        with self.subTest("Test missing relation"):
            volumeNumber = 3185
            eventQid = "Q11358"
            actual = self.wdSync.checkIfProceedingsFromExists(volumeNumber, eventQid)
            self.assertFalse(actual)


class TestDblpEndpoint(Basetest):
    """tests DblpEndpoint"""

    def setUp(self,debug=False,profile=True):
        super().setUp(debug, profile)
        self.endpointUrl = "https://qlever.cs.uni-freiburg.de/api/dblp/query"
        self.dblpEndpoint = DblpEndpoint(self.endpointUrl)

    @unittest.skipIf(Basetest.inPublicCI(), "queries unreliable wikidata endpoint")
    def test_getWikidataIdByVolumeNumber(self):
        """tests getWikidataIdByVolumeNumber"""
        test_params = [("1", ["conf/krdb/94"]), ("2400", ["conf/sebd/2019"]), ("-1", []), (3100, ["conf/psychobit/2021"])]
        for param in test_params:
            with self.subTest("test wikidata id query by volume number", param=param):
                number, expected = param
                actual = self.dblpEndpoint.getDblpIdByVolumeNumber(number)
                self.assertListEqual(expected, actual)

    def test_convertEntityIdToUrlId(self):
        """tests convertEntityIdToUrlId"""
        test_params = [("conf/aaai/2022", "conf/aaai/aaai2022"), ("conf/aaai", None),
                       ("conf/aaai/aaai2022", None), ("", None), (None, None)]
        for param in test_params:
            with self.subTest("test dblp id conversion", param=param):
                entityId, expected = param
                actual = self.dblpEndpoint.convertEntityIdToUrlId(entityId)
                self.assertEqual(expected, actual)

    @unittest.skipIf(Basetest.inPublicCI(), "queries unreliable wikidata endpoint")
    def test_toDblpUrl(self):
        """tests toDblpUrl"""
        test_params =[("conf/aaai/2022", False, "https://dblp.org/db/conf/aaai/aaai2022"),
                      ("conf/aaai/2022", True, "https://dblp.org/db/conf/aaai/aaai2022.html"),
                      ("conf/aaai/aaai2022", False, None),  # entity id is expected not the url id
                      (None, False, None), ("", False, None),(None, True, None), ("", True, None),
                      ("conf/aaai", False, None)]
        for param in test_params:
            with self.subTest("test dblp url generation", param=param):
                entityId, withPostfix, expected = param
                actual = self.dblpEndpoint.toDblpUrl(entityId, withPostfix)
                self.assertEqual(expected, actual)
