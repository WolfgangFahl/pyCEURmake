"""
Created on 2022-08-14

@author: wf
"""
import os.path
import pathlib
import re
import typing

from bs4 import BeautifulSoup, PageElement, NavigableString

from ceurws.utils.webscrape import ScrapeDescription, WebScrape
from ceurws.textparser import Textparser

class VolumeParser(Textparser):
    """
    CEUR-WS VolumeParser
    """

    def __init__(
            self,
            baseurl: str = 'http://ceur-ws.org',
            timeout: float = 3,
            showHtml: bool = False,
            debug: bool = False
    ):
        """
        Constructor

        Args:
            baseurl(str): the baseurl of the CEUR-WS website,
            timeout(float): the number of seconds to wait
            showHtml(bool): if True show the HTML code
            debug(bool): if True switch debugging on
        """
        Textparser.__init__(self, debug=debug)
        self.showHtml = showHtml
        self.baseurl = baseurl
        self.timeout = timeout
        self.scrape = WebScrape(timeout=timeout)
        
    def volumeUrl(self, volnumber: typing.Union[str, int]):
        """
        get the url for the given volume number

        Args:
            volnumber(str): the volume number

        Returns:
            str: url - the url of the volume
        """
        # e.g. http://ceur-ws.org/Vol-2635/
        url = f"{self.baseurl}/Vol-{volnumber}"
        return url

    def getSoup(self, url: str) -> BeautifulSoup:
        """
        get the beautiful Soup parser for the given url
        Args:
            url: url to parse

        Returns:
            parsed webpage
        """
        return self.scrape.getSoup(url, showHtml=self.showHtml, debug=self.debug)

    def get_volume_soup(self, number: int, use_cache: bool = True) -> typing.Optional[BeautifulSoup]:
        """
        Get Soup of the volume page for the given volume number
        Args:
            number: volume number of the volume to parse
            use_cache: If True use volume page from cache if present otherwise load from web and cache

        Returns:
            BeautifulSoup: soup of the volume page
            None: soup can not be loaded from cache or from web
        """
        html = self.get_volume_page(number, recache=not use_cache)
        if html is None:
            if self.debug:
                print(f"Vol-{number} could not be retrieved")
            return None
        soup = self.scrape.get_soup_from_string(html, show_html=self.showHtml)
        return soup

    def get_volume_page(self, number: int, recache: bool = False) -> typing.Union[str, None]:
        """
        Get the html content of the given volume number.
        Retrieves the volume page from cache or from ceur-ws.org
        Caches the volume page if not already cached
        Args:
            number: volume number
            recache: If True update the cache with a new fetch from the web. Otherwise, cache is used if present

        Returns:
            html of volume page or None if the volume page is not found
        """
        if not recache and VolumePageCache.is_cached(number):
            volume_page = VolumePageCache.get(number)
        else:
            url = self.volumeUrl(number)
            volume_page = self.scrape.get_html_from_url(url)
            VolumePageCache.cache(number, volume_page)
        return volume_page

    def parse_volume(self, number: int, use_cache: bool = True) -> typing.Tuple[dict,BeautifulSoup]:
        """
        parse the given volume
        caches the volume pages at ~/.ceurws/volumes

        Args:
            number: volume number of the volume to parse
            use_cache: If True use volume page from cache if present otherwise load from web and cache

        Returns:
            dict: extracted information
        """
        soup = self.get_volume_soup(number, use_cache=use_cache)
        parsed_dict = self.parse_soup(number,soup)
        return parsed_dict,soup
        
    def parse(self, url: str) -> dict:
        """
        parse the given url
        Args:
             url: URL to parse the volume information from

        Returns:
            dict: extracted information
        """
        soup = self.getSoup(url)
        parsed_dict = self.parse_soup(soup)
        return parsed_dict

    def parse_soup(self, number:str, soup: BeautifulSoup) -> dict:
        """
        parse the volume page data from the given soup
        
        Args:
            number(str): the volume number
            soup(BeautifulSoup): html parser to extract the content from

        Returns:
            dict: parsed content
        """
        if soup is None:
            return {
                "vol_number": number
            }
        # first try RDFa annotations
        scrapedDict = self.parseRDFa(soup)
        for key in scrapedDict:
            scrapedDict[key] = Textparser.sanitize(scrapedDict[key])
       
        # second part
        for descValue in ["description", "descripton"]:
            # descripton is a typo in the Volume index files not here!
            firstDesc = soup.find("meta", {"name": descValue})
            if firstDesc is not None:
                desc = firstDesc["content"]
                desc = Textparser.sanitize(desc, ["CEUR Workshop Proceedings "])
                scrapedDict["desc"] = desc
                break

        # first H1 has title info
        firstH1 = soup.find('h1')
        if firstH1 is not None:
            h1 = firstH1.text
            h1 = Textparser.sanitize(h1, ['<TD bgcolor="#FFFFFF">'])
            scrapedDict["h1"] = h1
            link = firstH1.find("a")
            if link is not None and len(link.text) < 20:
                acronym = link.text.strip()
                if not acronym:
                    if len(h1)<28:
                        acronym=h1
                    else:
                        acronym=h1.split()[0]
                    
                eventHomepage = link.attrs.get("href")
                scrapedDict["acronym"] = acronym
                scrapedDict["homepage"] = eventHomepage
            
        # first h3 has loctime
        firstH3 = soup.find('h3')
        if firstH3 is not None:
            h3 = firstH3.text
            h3 = Textparser.sanitize(h3)
            scrapedDict["h3"] = h3
            
        if self.hasValue(scrapedDict, "desc") and not self.hasValue(scrapedDict,"acronym"):
            scrapedDict["acronym"] = scrapedDict["desc"]
        if self.hasValue(scrapedDict, "h1") and not self.hasValue(scrapedDict, "title"):
            scrapedDict["title"] = scrapedDict["h1"]
        if self.hasValue(scrapedDict, "h1") and self.hasValue(scrapedDict, "title") and not self.hasValue(scrapedDict, "acronym"):
            scrapedDict["acronym"] = scrapedDict["h1"]
        #editorsRecords = self.parseEditors(soup)
        #scrapedDict["editors"] = editorsRecords
        return scrapedDict

    def parseEditors(self, soup: BeautifulSoup):
        """
        parse all editor information contained in the given soup
        parse all information between <b> Edited by </b> ... <hr>
        Args:
            soup: volume web page
        """
        if soup is None:
            return None
        possible_start_elements = soup.find_all("b")
        # find start
        start_elements = []
        for e in possible_start_elements:
            start_tags = ["edited by", "program committee"]
            for tag in start_tags:
                if tag in e.text.lower():
                    start_elements.append(e)
        if len(start_elements) == 0:
            return None
        edited_by = start_elements[0]
        editor_h3 = edited_by.find_next("h3")
        editor_records: typing.Dict[str, dict] = dict()
        if editor_h3 is None:
            return None
        editor_spans = editor_h3.find_all(attrs={"class": "CEURVOLEDITOR"})
        if editor_spans is not None and len(editor_spans) > 0:

            for editor_span in editor_spans:
                editor_name = editor_span.text
                editor = {"name": editor_name}
                if editor_span.parent.name == "a":
                    homepage = editor_span.parent.attrs.get("href", None)
                    editor["homepage"] = homepage
                    if editor_span.parent.next_sibling is not None:
                        affiliation_keys = editor_span.parent.next_sibling.text.strip()
                    else:
                        affiliation_keys = None
                else:
                    if editor_span.next_sibling is not None:
                        affiliation_keys = editor_span.next_sibling.text.strip()
                    else:
                        affiliation_keys = None
                if affiliation_keys is None or affiliation_keys == "":
                    sup = editor_span.find_next("sup")
                    if sup is not None:
                        affiliation_keys = sup.text.strip()
                editor["affiliation_keys"] = affiliation_keys
                editor_records[editor_name] = editor
        else:
            editor_elements = []
            group_elements = []
            if editor_h3.next_sibling and editor_h3.next_sibling.next_sibling and editor_h3.next_sibling.next_sibling.name == "h3":
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
            editor_keys = editor_record.get("affiliation_keys", "")
            if editor_keys is not None:
                keys = re.split('[, ]', editor_keys)
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
            start:

        Returns:
            dict
        """
        if start is None:
            return dict()
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

    def parseRDFa(self, soup: BeautifulSoup) -> dict:
        """
        tries to parse rdfa content from the given soup
        Args:
            soup: html parser to extract the content from

        Returns:
            dict: dict with the extracted content
        """
        scrapeDescr = [
            ScrapeDescription(key='volume_number', tag='span', attribute='class', value='CEURVOLNR'),
            ScrapeDescription(key='urn', tag='span', attribute='class', value='CEURURN'),
            ScrapeDescription(key='year', tag='span', attribute='class', value='CEURPUBYEAR'),
            ScrapeDescription(key='ceurpubdate', tag='span', attribute='class', value='CEURPUBDATE'),                        
            ScrapeDescription(key='acronym', tag='span', attribute='class', value='CEURVOLACRONYM'),
            ScrapeDescription(key='voltitle', tag='span', attribute='class', value='CEURVOLTITLE'),
            ScrapeDescription(key='title', tag='span', attribute='class', value='CEURFULLTITLE'),
            ScrapeDescription(key='loctime', tag='span', attribute='class', value='CEURLOCTIME'),
            ScrapeDescription(key='colocated', tag='span', attribute='class', value='CEURCOLOCATED')
        ]
        scrapedDict = self.scrape.parseWithScrapeDescription(soup, scrapeDescr)
        return scrapedDict


class VolumePageCache:
    """
    Cache interface for ceur-ws volume pages
    """

    cache_location = f"{pathlib.Path.home()}/.ceurws/volumes"

    @classmethod
    def is_cached(cls, number: int) -> bool:
        """
        Check if the volume page of the given volume number is cached
        Args:
            number: volume number of the volume page

        Returns:
            True if the corresponding volume page is cached
        """
        return os.path.exists(cls._get_volume_cache_path(number))

    @classmethod
    def cache(cls, number: int, html: typing.Union[str, bytes]):
        """
        cache the volume page corresponding to the given number
        Args:
            number: number of the volume to cache
            html: html of the volume page to cache
        """
        if html is None:
            return
        pathlib.Path(cls.cache_location).mkdir(parents=True, exist_ok=True)
        filename = cls._get_volume_cache_path(number)
        mode = "w"
        if isinstance(html, bytes):
            mode += "b"
        with open(filename, mode=mode) as f:
            f.write(html)

    @classmethod
    def _get_volume_cache_path(cls, number: int):
        """
        get the name of the volume cache file
        """
        return f"{cls.cache_location}/Vol-{number}.html"

    @classmethod
    def get(cls, number: int) -> typing.Union[str, bytes, None]:
        """
        Get the cached volume page of the given volume number.
        If the volume page is not cached None is returned.
        Args:
            number: volume number to retrieve

        Returns:
            str: cached volume page
            bytes: if the cached volume page contains encoding errors
            None: if no volume with the given number is cached
        """
        volume_page = None
        if cls.is_cached(number):
            filepath = cls._get_volume_cache_path(number)
            try:
                with open(filepath, mode="r") as f:
                    volume_page = f.read()
            except UnicodeDecodeError as _ex:
                with open(filepath, mode="rb") as f:
                    volume_page = f.read()
        return volume_page

    @classmethod
    def delete(cls, number: int):
        """
        Delete the cache corresponding to the given volume number
        Args:
            number: volume number
        """
        if cls.is_cached(number):
            filepath = cls._get_volume_cache_path(number)
            os.remove(filepath)
