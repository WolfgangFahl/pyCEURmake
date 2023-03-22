'''
Created on 2020-08-20

@author: wf

this is a redundant copy of the sources at https://github.com/WolfgangFahl/ConferenceCorpus/blob/main/corpus/datasources/webscrape.py
'''
import typing
import urllib.request
from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.request import build_opener, HTTPCookieProcessor
from bs4 import BeautifulSoup
import re

class WebScrape(object):
    '''
    WebScraper
    with a rudimentary Parser for https://en.wikipedia.org/wiki/RDFa
    extended for CEUR-WS and WikiCFP specific scraping
    
    https://stackoverflow.com/questions/21876602/what-does-the-html-typeof-attribute-do
    https://de.wikipedia.org/wiki/RDFa
    https://stackoverflow.com/questions/20767903/parsing-rdfa-in-html-xhtml
    https://www.w3.org/MarkUp/2009/rdfa-for-html-authors
    '''

    def __init__(
            self,
            debug: bool = False,
            showHtml: bool = False,
            timeout: float = 20,
            agent: str = 'Mozilla/5.0'
    ):
        """
        Constructor

        Args:
            debug(bool): if True show debugging information
            showHtml(bool): if True show the HTML retrieved
            timeout(float): the default timeout
            agent(str): the agent to mimic
        """
        self.err=None
        self.valid=False
        self.debug=debug
        self.showHtml=showHtml
        self.timeout=timeout
        self.agent=agent
        
    def findLinkForRegexp(self, regex: str):
        """
        find a link for the given regular expression

        Args:
            regex(str): the regular expression to find a link for

        Return:
            m(object),text(str): the match/text tuple or None,None
        """
        m=None
        text=None
        link=self.soup.find('a',href=re.compile(regex))
        if link:
            href=link['href']
            m=re.match(regex,href)    
            if hasattr(link, "text"):
                text=link.text 
        return m,text
        
    def fromTag(self, soup: BeautifulSoup, tag: str, attr: str = None, value: str = None, multi:bool=False):
        '''
        get metadata from a given tag, attribute and value
        e.g. <span class="CEURVOLACRONYM">DL4KG2020</span>
        
        tag=span, attr=class, value=CEURVOLACRONYM
        
        Args:
           soup(BeautifulSoup): the parser to work with
           tag(string): the tag to search
           attr(string): the attribute to expect
           value(string): the value to expect
           multi(bool): if True - return multiple values
        '''
        # https://stackoverflow.com/a/16248908/1497139
        # find a list of all tag elements
        if attr is not None and value is not None:
            nodes = soup.find_all(tag, {attr : value})
        else:
            nodes = soup.find_all(tag)    
        lines = [node.get_text() for node in nodes]
        if multi:
            return lines
        if len(lines)>0:
            return lines[0]
        else:
            return None
        
    def getSoup(self, url: str, showHtml: bool = False, debug:bool=False) -> BeautifulSoup:
        """
        get the beautiful Soup parser

        Args:
           url(str): the url to open
           showHtml(bool): if True  the html code should be pretty printed and shown
           debug(bool): if True debug info should be printed
        Return:
            BeautifulSoup: the html parser
        """
        html = self.get_html_from_url(url,debug=debug)
        return self.get_soup_from_string(html, show_html=showHtml)

    def get_soup_from_string(self, html: str, show_html: bool = False) -> BeautifulSoup:
        """
        get the beautiful Soup parser for the given html string

        Args:
            html: html content to parse
            show_html: True if the html code should be pretty printed and shown

        Returns:
            BeautifulSoup: the html parser
        """
        soup = BeautifulSoup(html, 'html.parser')
        if show_html:
            self.printPrettyHtml(soup)
        return soup
    
    def printPrettyHtml(self,soup):
        '''
        print the prettified html for the given soup
        
        Args:
            soup(BeuatifulSoup): the parsed html to print
        '''
        prettyHtml=soup.prettify()
        print(prettyHtml)   
            
    def parseWithScrapeDescription(
            self,
            soup: BeautifulSoup,
            scrapeDescr: typing.Union[typing.List['ScrapeDescription'], None] = None
    ) -> dict:
        """
        parse the given url with the given encoding
        Args:
            soup: html parser to parse the content from
            scrapeDescr: description of the

        Return:
             a dict with the results
        """
        scrapeDict = dict()
        for scrapeItem in scrapeDescr:
            value = self.fromTag(soup, scrapeItem.tag, scrapeItem.attribute, scrapeItem.value, multi=scrapeItem.multi)
            scrapeDict[scrapeItem.key] = value
        self.valid = True
        return scrapeDict
                
    def parseRDFa(self,url):
        '''
        rudimentary RDFa parsing
        '''
        triples=[]    
        try:
            self.soup=self.getSoup(url, self.showHtml)         
            subjectNodes = self.soup.find_all(True, {'typeof' : True})
            for subjectNode in subjectNodes:
                subject=subjectNode.attrs['typeof']
                if self.debug:
                    print(subjectNode)
                for predicateNode in subjectNode.find_all():
                    value=None 
                    name=None
                    if 'content' in predicateNode.attrs:
                        value=predicateNode.attrs['content']
                    else:
                        value=predicateNode.get_text()    
                    if 'property' in predicateNode.attrs:
                        name=predicateNode.attrs['property'] 
                    if name is not None and value is not None:
                        triples.append((subject,name,value))
            self.valid=True
        except HTTPError as herr:
            self.err=herr
        except urllib.error.URLError as terr:
            self.err=terr
        return triples

    def get_html_from_url(self, url: str,debug:bool=False) -> typing.Union[str, bytes, None]:
        """
        Get the html response from the given url
        Args:
            url: url to the get the content from
            debug(bool): if True show non available volumes

        Returns:
            str: content of the url as string
            bytes: If the content of the url contains encoding errors
            None: If the url is not reachable
        """
        req = urllib.request.Request(url, headers={'User-Agent': f'{self.agent}'})
        # handle cookies
        opener = build_opener(HTTPCookieProcessor())
        try:
            response = opener.open(req, timeout=self.timeout)
        except HTTPError as herr:
            self.err = herr
            if debug:
                print(f"{url.split('/')[-1]} not available")
            return None
        html = response.read()
        try:
            html = html.decode(response.headers.get_content_charset())
        except UnicodeDecodeError as ex:
            print(f"ERROR: Could not properly decode the html code of <{url}>")
            print(ex)
        return html


@dataclass
class ScrapeDescription:
    """
    Description of rdfa elements to scrape
    """
    key: str
    tag: str  # the tag to search
    attribute: str  # the attribute to expect
    value: str  # the value to expect
    multi: bool=False # do we expect multiple elements?
    