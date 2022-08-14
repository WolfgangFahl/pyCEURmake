'''
Created on 2022-08-14

@author: wf
'''
from utils.webscrape import WebScrape
class VolumeParser:
    '''
    CEUR-WS VolumeParser
    '''
    def __init__(self,baseurl:str='http://ceur-ws.org',timeout=3):
        '''
        constructor
        '''
        self.baseurl=baseurl
        self.timeout=timeout
        self.scrape=WebScrape(timeout=timeout)
        pass

    def parseRDFa(self,volnumber):
        '''
        parse RDFa of the given volume number
        Args:
            volnumber(str): the volume number
        '''
        # e.g. http://ceur-ws.org/Vol-2635/
        url=f"{self.baseurl}/Vol-{volnumber}"
        
        scrapeDescr=[
            {'key':'acronym', 'tag':'span','attribute':'class', 'value':'CEURVOLACRONYM'},
            {'key':'title',   'tag':'span','attribute':'class', 'value':'CEURFULLTITLE'},
            {'key':'loctime', 'tag':'span','attribute':'class', 'value':'CEURLOCTIME'}
        ]
        scrapedDict=self.scrape.parseWithScrapeDescription(url,scrapeDescr)
        valid=self.scrape.valid
        err=self.scrape.err
        return valid,err,scrapedDict