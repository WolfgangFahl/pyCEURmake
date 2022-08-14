'''
Created on 2022-08-14

@author: wf
'''
from utils.webscrape import WebScrape
class VolumeParser:
    '''
    VolumeParser
    '''
    def __init__(self,baseurl:str='http://ceur-ws.org'):
        '''
        constructor
        '''
        self.baseurl=baseurl
        pass

    def parse(self,volnumber):
        '''
        parse RDFa of the given volume number
        Args:
            volnumber(str): the volume number
        '''
        # e.g. http://ceur-ws.org/Vol-2635/
        url=f"{self.baseurl}/Vol-{volnumber}"
        scrape=WebScrape()
        scrapeDescr=[
            {'key':'acronym', 'tag':'span','attribute':'class', 'value':'CEURVOLACRONYM'},
            {'key':'title',   'tag':'span','attribute':'class', 'value':'CEURFULLTITLE'},
            {'key':'loctime', 'tag':'span','attribute':'class', 'value':'CEURLOCTIME'}
        ]
        scrapedDict=scrape.parseWithScrapeDescription(url,scrapeDescr)
        valid=scrape.valid
        err=scrape.err
        return valid,err,scrapedDict