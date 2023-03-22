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
from tqdm import tqdm
from collections import Counter

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
        
    def check_paper_toc_parser(self,vol_number:str,counter:Counter,debug:bool=False,show_failure:bool=True):
        record,soup = self.volumeParser.parse_volume(vol_number)
        if debug:
            print(json.dumps(record,indent=2))
        if soup:
            try: 
                ptp=PaperTocParser(number=vol_number,soup=soup,debug=debug)
                paper_records=ptp.parsePapers()
                if debug:
                    print(json.dumps(paper_records,indent=2))
                for paper_record in paper_records:
                    for key in paper_record:
                        counter[key]+=1
            except Exception as ex:
                counter["failure"]+=1
                if show_failure:
                    print(f"{vol_number} paper toc parsing fails with {str(ex)})")
        
    def test_volExamples(self):
        """
        tests parsing of volume examples
        """
        vol_numbers = [3264,3343]
        counter=Counter()
        debug=self.debug
        debug=True
        for vol_number in vol_numbers:
            self.check_paper_toc_parser(vol_number, counter, debug)
        if debug:
            print(counter.most_common())
               
    def test_parse_all_papertocs(self):
        """
        test parsing all paper table of contents
        """
        debug=self.debug
        t=None
        progress=False
        counter=Counter()
        if progress:
            t=tqdm(total=len(self.volumeList))
        for volume in self.volumeList:
            self.check_paper_toc_parser(volume.number, counter, debug)
            if t:
                t.description=f"{volume.number}"
                t.update()
        print(counter.most_common())
            
       
    
