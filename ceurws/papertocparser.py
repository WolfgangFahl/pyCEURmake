'''
Created on 2023-03-22

@author: wf
'''
from bs4 import BeautifulSoup
from ceurws.textparser import Textparser
from ceurws.utils.webscrape import ScrapeDescription, WebScrape
import re
class PaperTocParser(Textparser):
    """
    parser for paper table of contents
    """
    
    def __init__(self,number:str,soup:BeautifulSoup,debug:bool=False):
        """
        constructor
        
        Args:
            number(str): the volume number
            soup(BeautifulSoup): the parser input
            debug(bool): if True print out debug info
        """
        Textparser.__init__(self, debug=debug)
        self.number=number
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
        if toc:
            for paper_li in toc.findAll('li'):
                paper_record = self.scrape.parseWithScrapeDescription(paper_li, self.scrapeDescr)
                paper_record["vol_number"]=self.number
                href=paper_li.find('a', href=True)
                if href:
                    paper_record["pdf_name"]=href.attrs["href"]
                if "id" in paper_li.attrs:
                    paper_record["id"]=paper_li.attrs["id"]
                paper_records.append(paper_record)
                pass
        else: 
            toc=self.soup.find('h2',text=re.compile(".*Contents.*"))
            if toc:
                for paper_li in self.soup.find_all('li',recursive=True):
                    href_node=paper_li.find('a', href=True)
                    if href_node:
                        href=href_node.attrs["href"]
                        if ".pdf" in href:
                            title=Textparser.sanitize(href_node.text)
                            author_part=(paper_li.find('br').next_sibling)
                            authors=author_part.text
                            authors=Textparser.sanitize(authors)
                            author_list=authors.split(",")
                            for i,author in enumerate(author_list):
                                author_list[i]=author.strip()
                            paper_record={
                                "vol_number":self.number,
                                "title": title,
                                "pdf_name": href,
                                "authors": author_list
                            }
                            paper_records.append(paper_record)
            else:
                if self.debug:
                    print(f"no toc for {self.number}")
        return paper_records
        
    
