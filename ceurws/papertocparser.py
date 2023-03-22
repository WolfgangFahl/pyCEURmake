'''
Created on 2023-03-22

@author: wf
'''
from bs4 import BeautifulSoup
from ceurws.textparser import Textparser
from ceurws.utils.webscrape import ScrapeDescription, WebScrape

class PaperTocParser(Textparser):
    """
    parser for paper table of contents
    """
    
    def __init__(self,soup:BeautifulSoup,debug:bool=False):
        """
        constructor
        
        Args:
            soup(BeautifulSoup): the parser input
            debug(bool): if True print out debug info
        """
        Textparser.__init__(self, debug=debug)
        self.soup=soup
        self.scrape = WebScrape()
        self.scrapeDescr = [
            ScrapeDescription(key='title', tag='span', attribute='class', value='CEURTITLE'),
            ScrapeDescription(key='authors', tag='span', attribute='class', value='CEURAUTHOR', multi=True),
            #ScrapeDescription(key='submitted_papers', tag='span', attribute='class', value='CEURSUBMITTEDPAPERS'),
            #ScrapeDescription(key='accepted_papers', tag='span', attribute='class', value='CEURACCEPTEDPAPERS'),
        ]
        
    def parsePapers(self):
        """
        parse the toc to papers
        """
        paper_records=[]
        toc=self.soup.find(attrs={"class": "CEURTOC"})
        for paper_li in toc.findAll('li'):
            paper_record = self.scrape.parseWithScrapeDescription(paper_li, self.scrapeDescr)
            paper_record["id"]=paper_li.attrs["id"]
            paper_records.append(paper_record)
            pass
        return paper_records
        
    
