'''
Created on 2022-08-14

@author: wf
'''
import re
import typing

from bs4 import BeautifulSoup, PageElement, NavigableString

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
        
    def volumeUrl(self, volnumber: typing.Union[str, int]):
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

    def getSoup(self, url: str) -> BeautifulSoup:
        """
        get the beautiful Soup parser for the given url
        Args:
            url: url to parse

        Returns:
            parsed webpage
        """
        return self.scrape.getSoup(url, showHtml=self.showHtml)
        
    def parse(self, url: str) -> dict:
        '''
        parse the given url
        Args:
             url: URL to parse the volume information from

         Returns:
             extracted information
        '''
        # first try RDFa annotations
        _valid,_err,scrapedDict=self.parseRDFa(url)
        for key in scrapedDict:
            scrapedDict[key]=Textparser.sanitize(scrapedDict[key])
        
        # second part
        soup = self.getSoup(url)
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

    def parseEditors(self, soup: BeautifulSoup):
        """
        parse all editor information contained in the given soup
        parse all information between <b> Edited by </b> ... <hr>
        Args:
            soup: volume web page
        """
        possible_start_elements = soup.find_all("b")
        edited_by = [e for e in possible_start_elements if "edited by" in e.text.lower()][0]
        editor_h3 = edited_by.find_next("h3")
        editor_records: typing.Dict[str, dict] = dict()
        editor_spans = editor_h3.find_all(attrs={"class":"CEURVOLEDITOR"})
        if editor_spans is not None and len(editor_spans) > 0:

            for editor_span in editor_spans:
                editor_name = editor_span.text
                editor = {"name": editor_name}
                if editor_span.parent.name == "a":
                    homepage = editor_span.parent.attrs.get("href", None)
                    editor["homepage"] = homepage
                    affiliation_keys = editor_span.parent.next_sibling.text.strip()
                else:
                    affiliation_keys = editor_span.next_sibling.text.strip()
                if affiliation_keys is None or affiliation_keys == "":
                    sup = editor_span.find_next("sup")
                    if sup is not None:
                        affiliation_keys = sup.text
                editor["affiliation_keys"] = affiliation_keys.strip()
                editor_records[editor_name] = editor
        else:
            editor_elements = []
            group_elements = []
            if editor_h3.next_sibling.next_sibling.name == "h3":
                while editor_h3.next_sibling.next_sibling.name == "h3" and editor_h3.text.strip() != "":
                    editor_elements.append(editor_h3.contents)
                    editor_h3 = editor_h3.next_sibling.next_sibling
            else:
                for child in editor_h3.childGenerator():
                    if child.name == "br":
                        editor_elements.append(group_elements)
                        group_elements = []
                    else:
                        group_elements.append(child)
            for elements in editor_elements:
                text = "".join([e.text for e in elements]).strip()
                affiliation_key = text.split(" ")[-1]
                editor_name = text[:-len(affiliation_key)]
                links = [e for e in elements if e.name == "a"]
                if len(links) > 0:
                    homepage = links[0].attrs.get("href", None)
                else:
                    homepage = None
                editor = {"name": editor_name, "homepage": homepage, "affiliation_key": affiliation_key}
                editor_records[editor_name] = editor
        affiliation_keys = {editor.get("affiliation_key")
                            for editor in editor_records.values()
                            if editor.get("affiliation_key", None) is not None}
        affiliation_map = self.parseAffiliationMap(editor_h3.next_sibling)
        for editor_record in editor_records.values():
            keys = re.split('[, ]', editor_record.get("affiliation_keys", ""))
            editor_affiliations = []
            for key in keys:
                if key in affiliation_map:
                    editor_affiliations.append(affiliation_map.get(key.strip()))
            editor_record["affiliation"] = editor_affiliations
        return editor_records

    def parseAffiliationMap(self, start: PageElement) -> dict:
        """
        Parse out the affiliations and their reference key
        Args:
            soup:

        Returns:
            dict
        """
        end = start.find_next("hr")
        affiliations_elements = []
        group_elements = []
        for element in start.previous.nextGenerator():
            if element.name in ["br", "hr"]:
                affiliations_elements.append(group_elements)
                group_elements = []
            elif isinstance(element, NavigableString) and element.text.strip() == "":
                pass
            elif element.name == "h3":
                # elements inside the element are included through the nextGenerator
                pass
            else:
                group_elements.append(element)
            if element == end:
                break
        affiliations_elements = [x for x in affiliations_elements if x != []]
        affiliation_map = dict()
        for elements in affiliations_elements:
            if isinstance(elements[0], NavigableString) and " " in elements[0].text.strip():
                text_containing_key = elements[0].text.strip()
                key = text_containing_key.split(" ")[0]
                key_element = NavigableString(value=key)
                text_element = NavigableString(value=text_containing_key[len(key):])
                elements = [key_element, text_element, *elements[1:]]
            key = elements[0].text.strip()
            text_elements = []
            link_elements = []
            for element in elements[1:]:
                if isinstance(element, NavigableString):
                    text_elements.append(element)
                elif element.name == "a":
                    link_elements.append(element)
            affiliation = "".join([elem.text for elem in text_elements])
            affiliation = affiliation.replace("\n", "").replace("\t", "").replace("\r", "")
            if affiliation.startswith(key):
                affiliation = affiliation[len(key):]
            homepages = []
            for element in link_elements:
                if hasattr(element, "attrs") and element.attrs.get("href", None) is not None:
                    homepage = element.attrs.get("href", None)
                    homepages.append(homepage)
            if key is not None and key != "":
                key = key.strip(".")
                affiliation_map[key] = {"name": affiliation, "homepage": homepages}
        return affiliation_map



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