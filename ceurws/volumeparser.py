'''
Created on 2022-08-14

@author: wf
'''
from utils.webscrape import WebScrape
from ceurws.textparser import Textparser

class VolumeParser(Textparser):
    '''
    CEUR-WS VolumeParser
    '''
    def __init__(self,baseurl:str='http://ceur-ws.org',timeout=3,showHtml:bool=False,debug:bool=False):
        '''
        Constructor
        
        Args:
            baseurl(str): the baseurl of the CEUR-WS website,
            timeout(float): the number of seconds to wait
            showHtml(bool): if True show the HTML code
            debug(bool): if TRUE switch debugging on
        '''
        Textparser.__init__(self,debug=debug)
        self.showHtml=showHtml
        self.baseurl=baseurl
        self.timeout=timeout
        self.scrape=WebScrape(timeout=timeout)
        
    def volumeUrl(self,volnumber):
        '''
        get the url for the given volume number
        
        Args:
            volnumber(str): the volume number
            
        Returns:
            str: url - the url of the volume
        '''
        # e.g. http://ceur-ws.org/Vol-2635/
        url=f"{self.baseurl}/Vol-{volnumber}"
        return url
        
    def parse(self,url):
        '''
        parse the given url
        '''
        # first try RDFa annotations
        _valid,_err,scrapedDict=self.parseRDFa(url)
        for key in scrapedDict:
            scrapedDict[key]=Textparser.sanitize(scrapedDict[key])
        
        # second part
        soup=self.scrape.getSoup(url, showHtml=self.showHtml)
        for descValue in ["description","descripton"]:
            # descripton is a typo in the Volume index files not here!
            firstDesc=soup.find("meta", {"name" : descValue})
            if firstDesc is not None:
                desc=firstDesc["content"]
                desc=Textparser.sanitize(desc,["CEUR Workshop Proceedings "])
                scrapedDict["desc"]=desc
                break

        # first H1 has title info
        firstH1=soup.find('h1')
        if firstH1 is not None:
            if len(firstH1.contents[0].text) < 20:
                scrapedDict["acronym"] = firstH1.contents[0].text
            h1=firstH1.text
            h1=Textparser.sanitize(h1,['<TD bgcolor="#FFFFFF">'])
            scrapedDict["h1"]=h1
            link = firstH1.find("a")
            if link is not None and len(link.text) < 20:
                acronym = link.text
                eventHomepage = link.attrs.get("href")
                scrapedDict["acronym"] = acronym
                scrapedDict["homepage"] = eventHomepage
            
        # first h3 has loctime
        firstH3=soup.find('h3')
        if firstH3 is not None:
            h3=firstH3.text
            h3=Textparser.sanitize(h3)
            scrapedDict["h3"]=h3
            
        if self.hasValue(scrapedDict, "desc") and not self.hasValue(scrapedDict,"acronym"):
            scrapedDict["acronym"]=scrapedDict["desc"]
        if self.hasValue(scrapedDict, "h1") and not self.hasValue(scrapedDict,"title"):
            scrapedDict["title"]=scrapedDict["h1"]
        if self.hasValue(scrapedDict, "h1") and self.hasValue(scrapedDict, "title") and not self.hasValue(scrapedDict, "acronym"):
            scrapedDict["acronym"] = scrapedDict["h1"]
            
        return scrapedDict

    def parseRDFa(self,url):
        scrapeDescr=[
            {'key':'acronym', 'tag':'span','attribute':'class', 'value':'CEURVOLACRONYM'},
            {'key':'title',   'tag':'span','attribute':'class', 'value':'CEURFULLTITLE'},
            {'key':'loctime', 'tag':'span','attribute':'class', 'value':'CEURLOCTIME'},
            {'key':'colocated', 'tag':'span','attribute':'class', 'value':'CEURCOLOCATED'}
        ]
        scrapedDict=self.scrape.parseWithScrapeDescription(url,scrapeDescr)
        valid=self.scrape.valid
        err=self.scrape.err
        return valid,err,scrapedDict