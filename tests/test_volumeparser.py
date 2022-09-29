'''
Created on 2022-08-14

@author: wf
'''
import pprint
import time
import unittest

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

    def test_issue30(self):
        """
        tests why the extraction of the acronym fails for some volumes
        """
        volumeWithKnownIssue = "435"
        volumeUrl = self.volumeParser.volumeUrl(volumeWithKnownIssue)
        scrapedDict=self.volumeParser.parse(volumeUrl)
        self.assertEqual("SWAT4LS 2008", scrapedDict.get("acronym"))
        self.assertEqual("http://www.swat4ls.org/", scrapedDict.get("homepage"))
        print(scrapedDict)

    def test_parseEditors(self):
        """
        tests parseEditors
        """
        test_params = [  # (volumeNumber, #editors, #editorHomepages, #affiliations)
            (3200, 8, 3, 6), (3100, 2, 0, 1), (3000, 2, 1, 2), (2800, 2, 0, 2), (2500, 2, 2, 0), (2000, 5, 4, 4),
            (1500, 5, 5, 5), (1000, 9, 1, 6), (700, 3, 1, 2), (600, 1, 0, 1),
            # (500, 3, 3, 2),
            # (550, 2, 2, 2),
            # (250, 7, 7, 5),
            # (200, 3, 3, 1), (100, 4, 4, 3), (50, 2, 1, 2), (10, 3, 3, 3), (1, 4, 0, 2),
            (3212, 2, 2, 2),  # multiple affiliations for one editor
            # (3211, 5, 5, 5),  # affiliation missing → error on volume page
            (3207, 5, 4, 7),  # sup with link to affiliation
            (3203, 2, 2, 3),  # multiple affiliations for one editor with reference seperator
            (3199, 4, 0, 4),  # sup without link to affiliation (reference and key different)
            (3188, 4, 0, 3),
            (3148, 2, 1, 3),
            (3139, 3, 3, 3),
            # (3127, 9, 0, 9),  # special case of editor definition
            # (3116, 2, 2, 2),  # affiliation reference included in link
        ]
        for param in test_params[0:]:
            with self.subTest(f"test editor parsing for Vol-{param[0]}", param=param):
                number, exp_editors, exp_homepages, exp_affiliations = param
                url = self.volumeParser.volumeUrl(number)
                soup = self.volumeParser.getSoup(url)
                res = self.volumeParser.parseEditors(soup)
                #pprint.pprint(res)
                number_of_editors = len(res)
                number_of_hompages = len(
                        [e.get("homepage")
                         for e in res.values()
                         if e.get("homepage", None) is not None])
                affiliations = []
                for e in res.values():
                    affiliations.extend([a.get("name") for a in e.get("affiliation")])
                number_of_affiliations = len(set(affiliations))
                print(
                    f"Vol-{number}:#editors={number_of_editors} #hompages={number_of_hompages} #affiliations={number_of_affiliations} ({url})")
                self.assertEqual(exp_editors, number_of_editors)
                self.assertEqual(exp_homepages, number_of_hompages)
                self.assertEqual(exp_affiliations, number_of_affiliations)

    @unittest.skipIf(True, "Only for manual testing")
    def test_parseEditors_stressTest(self):
        """
        ToDo: How many can I extract correctly?
        """
        total = 3225
        end = 600
        with open("/tmp/log_ceurws_editor_parsing.txt", mode="a") as fp:
            for i in range(total, end, -1):
                if i%100 == 0:
                    time.sleep(10)
                url = self.volumeParser.volumeUrl(i)
                soup = self.volumeParser.getSoup(url)
                msg = f"({i:04}/{total})"
                try:
                    res = self.volumeParser.parseEditors(soup)
                except Exception as ex:
                    msg += " ❌ Error"
                    res = None
                    print(ex)
                if res is not None:
                    number_of_editors = len(res)
                    number_of_hompages = len([e.get("homepage") for e in res.values() if e.get("homepage", None) is not None])
                    affiliations = []
                    for e in res.values():
                        affiliations.extend([a.get("name") for a in e.get("affiliation")])
                    number_of_affiliation = len(set(affiliations))
                    number_of_editors_with_affiliations = len([True for e in res.values() if e.get("affiliation", None) is not None])
                    something_fishy = "❌" if number_of_editors !=number_of_editors_with_affiliations else ""
                    msg += f"{something_fishy} #editors={number_of_editors} #affiliations={number_of_affiliation} #hompages={number_of_hompages} ({url})"
                print(msg)
                fp.write(msg+"\n")