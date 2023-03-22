"""
Created on 2022-08-14

@author: wf
"""
import json
import time
import unittest

import requests

from tests.basetest import Basetest
from ceurws.volumeparser import VolumePageCache, VolumeParser
from ceurws.ceur_ws import VolumeManager
from lodstorage.lod import LOD

class TestVolumeParser(Basetest):
    """
    Test parsing Volume pages
    """
    
    def setUp(self, debug=False, profile=True):
        """
        setUp the tests
        """
        Basetest.setUp(self, debug=debug, profile=profile)
        self.url= 'http://ceur-ws.org'
        self.volumeParser=VolumeParser(self.url,showHtml=False)
        self.vm=VolumeManager()
        self.vm.load()
        self.volumeList=self.vm.getList()
        self.volumesByNumber, _duplicates = LOD.getLookup(self.volumeList, 'number')
        
    def testVolumeParser(self):
        """
        test the volumeparser
        """
        debug = self.debug
        # title >=559
        # acronym > = 901
        dolimit = self.inPublicCI()
        # dolimit = True
        debug = True
        if dolimit: 
            start = 745
            limit = 746
        else: 
            start = 1
            limit = len(self.volumeList)+1
        for volnumber in range(start,limit):
            scrapedDict,_soup = self.volumeParser.parse_volume(volnumber, use_cache=True)
            if debug:
                print(f"Vol-{volnumber}:{scrapedDict}")
                
    def testIssue41(self):
        """
        test issue 41
        https://github.com/WolfgangFahl/pyCEURmake/issues/41
        'NavigableString' object has no attribute 'text'
        """
        testcases=[(49,"DL-2001"),(40,"Semantic Web Workshop 2001")]
        debug=True
        for volnumber,expected_acronym in testcases:
            scrapedDict,_soup=self.volumeParser.parse_volume(volnumber, use_cache=False)
            if debug:
                print(scrapedDict)
            self.assertEqual(expected_acronym,scrapedDict["acronym"])
            
    def testLocTime(self):
        """
        test the loctime parts and splits
        """
        for volnumber, volume in self.volumesByNumber.items():
            parts=[]
            if hasattr(volume,"loctime") and volume.loctime is not None:
                parts=volume.loctime.split(",")
                print(f"{volnumber:4}({len(parts)}):{volume.loctime}")

    def test_issue30(self):
        """
        tests why the extraction of the acronym fails for some volumes
        """
        volumeWithKnownIssue = 435
        scrapedDict,_soup=self.volumeParser.parse_volume(volumeWithKnownIssue)
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
            (2196, 10, 10, 10)
        ]
        for param in test_params[0:]:
            with self.subTest(f"test editor parsing for Vol-{param[0]}", param=param):
                number, exp_editors, exp_homepages, exp_affiliations = param
                url = self.volumeParser.volumeUrl(number)
                soup = self.volumeParser.getSoup(url)
                res = self.volumeParser.parseEditors(soup)
                #pprint.pprint(res)
                number_of_editors = len(res)
                number_of_homepages = len(
                        [e.get("homepage")
                         for e in res.values()
                         if e.get("homepage", None) is not None])
                affiliations = []
                for e in res.values():
                    affiliations.extend([a.get("name") for a in e.get("affiliation")])
                number_of_affiliations = len(set(affiliations))
                print(
                    f"Vol-{number}:#editors={number_of_editors} #homepages={number_of_homepages} #affiliations={number_of_affiliations} ({url})")
                self.assertEqual(exp_editors, number_of_editors)
                self.assertEqual(exp_homepages, number_of_homepages)
                self.assertEqual(exp_affiliations, number_of_affiliations)

    @unittest.skipIf(True, "Only for manual testing")
    def test_parseEditors_stressTest(self):
        """
        ToDo: How many can I extract correctly?
        """
        total = 3225
        end = 600
        log_file = "log_ceurws_editor_parsing.txt"
        count_editors = 0
        count_affiliations = 0
        count_homepages = 0
        with open(log_file, mode="a") as fp:
            for i in range(total, end, -1):
                if i%50 == 0:
                    time.sleep(30)
                url = self.volumeParser.volumeUrl(i)
                soup = self.volumeParser.getSoup(url)
                msg = f"({i:04}/{total})"
                try:
                    res = self.volumeParser.parseEditors(soup)
                    with open("/tmp/editors.json", mode="a", encoding='utf8') as f:
                        json.dump(res, fp=f, ensure_ascii=False)
                        f.write("\n")
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
                    number_of_editors_with_affiliations = len([True
                                                               for e in res.values()
                                                               if e.get("affiliation", None) is not None
                                                               and e.get("affiliation", "") != ""])
                    error_msg = "❌" if number_of_editors != number_of_editors_with_affiliations else ""
                    msg += f"{error_msg} #editors={number_of_editors} #affiliations={number_of_affiliation} #hompages={number_of_hompages} ({url})"
                    count_editors += int(number_of_editors)
                    count_homepages += int(number_of_hompages)
                    count_affiliations += int(number_of_affiliation)
                print(msg)
                fp.write(msg+"\n")
        print("count_editors:", count_editors,
              "count_affiliations:", count_affiliations,
              "count_homepages:", count_homepages)

    @unittest.skip
    def test_parseEditor(self):
        total = 3354
        end = 0
        log_file = "log_ceurws_editor_parsing.txt"
        volume_editors = dict()
        for vol_num in range(total, end, -1):
            print(vol_num)
            soup = self.volumeParser.get_volume_soup(vol_num)
            editors = self.volumeParser.parseEditors(soup)
            volume_editors[f"Vol-{vol_num}"] = editors
        with open(log_file, mode="w") as fp:
            json.dump(volume_editors, fp, indent=4)

    @unittest.skipIf(True, "Analyses how often rdfa is used on the volume pages")
    def test_rdfa(self):
        count = 0
        for i in range(3231, 1, -1):
            if i % 200 == 0:
                time.sleep(20)
            print(f"{i:04}/3230)", end="")
            url = f"https://ceur-ws.org/Vol-{i}/"
            resp = requests.get(url)
            if resp.status_code != 200:
                print("error", end="")
            pageStatement = 'prefix="'
            if pageStatement in resp.text:
                count += 1
                print(url, end="")
            elif pageStatement in f'<link rel="foaf:page" href="{url}">':
                count += 1
                print(url, end="")
            elif pageStatement in f'foaf:name':
                count += 1
                print(url, end="")
            print("")
        print(count)

    def test_vol3264(self):
        """
        tests parsing of volume 3264
        """
        vol_number = 3264
        record,_soup = self.volumeParser.parse_volume(vol_number)
        debug=self.debug
        #debug=True
        if debug:
            print(json.dumps(record,indent=2))
        expected={
            "volume_number": "Vol-3264",
            "urn": "urn:nbn:de:0074-3264-7",
            "year": "2022",
            "ceurpubdate": "2022-11-05",
            "acronym": "HEDA 2022",
            "voltitle": "The International Health Data Workshop HEDA 2022",
            "title": "Proceedings of The International Health Data Workshop",
            "loctime": "Bergen, Norway, June 26th-27th, 2022",
            "colocated": "Petri Nets 2022",
            "h1": "HEDA 2022 The International Health Data Workshop HEDA 2022",
            "homepage": "",
            "h3": "Proceedings of The International Health Data Workshop co-located with 10th International Conference on Petrinets (Petri Nets 2022)"
        }
        self.assertEqual(expected,record)

    def test_volume_caching(self):
        """
        tests caching of volumes
        """
        vol = 3000
        VolumePageCache.delete(number=vol)
        self.assertFalse(VolumePageCache.is_cached(vol))
        self.volumeParser.get_volume_page(vol)
        self.assertTrue(VolumePageCache.is_cached(vol))
        VolumePageCache.delete(number=vol)
        self.assertFalse(VolumePageCache.is_cached(vol))

    def test_extraction_of_event_homepages(self):
        """
        tests parsing the event homepage from the volume page
        """
        start = 3190
        limit = 3200
        homepages = []
        for volnumber in range(start, limit):
            scrapedDict,_soup = self.volumeParser.parse_volume(volnumber, use_cache=True)
            homepage = scrapedDict.get("homepage", None)
            if homepage is not None and homepage.startswith("http"):
                homepages.append(scrapedDict["homepage"].strip())
                # print(volnumber, scrapedDict["homepage"])
        print(f"Found {len(homepages)} event homepages")
        print(f"Found {len(set(homepages))} unique event homepages")
