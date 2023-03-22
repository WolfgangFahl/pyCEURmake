import calendar
import datetime
import os

import re
import typing

import dateutil.parser
from lodstorage.entity import EntityManager
from lodstorage.jsonable import JSONAble
from lodstorage.storageconfig import StorageConfig
from urllib.request import Request, urlopen
from pathlib import Path
from ceurws.indexparser import IndexHtmlParser
from ceurws.papertocparser import PaperTocParser
from ceurws.volumeparser import VolumeParser
from ceurws.utils.download import Download
from geograpy.locator import City, Country, Location, LocationContext, Region
from tqdm import tqdm
from bs4 import BeautifulSoup

class CEURWS:
    '''
    CEUR-WS 
    '''
    URL="http://ceur-ws.org"
    home = str(Path.home())
    CACHE_DIR = "%s/.ceurws" % home
    CACHE_FILE=f"{CACHE_DIR}/ceurws.db"
    CACHE_HTML=f"{CACHE_DIR}/index.html"
    CONFIG=StorageConfig(cacheFile=CACHE_FILE)

class Volume(JSONAble):
    """
    Represents a volume in ceur-ws
    """

    def getSamples(self):
        samples=[
            {
                "number": 2436,
                "url": "http://ceur-ws.org/Vol-2436/",
                "title": "Evaluation and Experimental Design in Data Mining and Machine Learning",
                "fullTitle": "1st Workshop on Evaluation and Experimental Design in Data Mining and Machine Learning",
                "acronym": "EDML 2019",
                "lang": "en",
                "location": "Calgary, Alberta, Canada",
                "country": "Canada",
                "region":"Alberta",
                "city": "Calgary",
                "ordinal": 1,
                "date":datetime.datetime(year=2019, month=5, day=4),
                "dateFrom":"",
                "dateTo":"",
                "pubYear":2019,
                "pubDate":"2019-09-08",
                "submitDate":"2019-07-28",
                "valid": True,
                "conference": Conference,
                "editors":[Editor],
                "sessions":[Session],
                "virtualEvent": False
            }
        ]
        return samples

    def getVolumeNumber(self):
        """
        get number of the volume
        """
        number = getattr(self, "number", "Volume has no number")
        return number

    def getVolumeUrl(self) -> typing.Union[str, None]:
        """
        get the url of the volume page
        """
        number = getattr(self, "number")
        url = self.getVolumeUrlOf(number)
        return url

    @staticmethod
    def getVolumeUrlOf(number: typing.Union[str, int]) -> typing.Union[str, None]:
        """
        get the volume url of the given volume number
        Args:
            number: volume number
        """
        url = None
        if number is not None:
            url = f"http://ceur-ws.org/Vol-{number}/"
        return url

    def isVirtualEvent(self) -> bool:
        """
        Returns True if the event is a virtual event
        """
        return getattr(self, "virtualEvent", False)

    def normalize(self):
        """
        Tries to normalize the properties e.g. breaking loctime into designated location and time properties
        Example: 'Vienna, Austria, July 25th, 2022'
        """
        pass

    def resolveLoctime(self):
        """
        Resolve the loctime property by breaking it down to city, region, country, dateFrom, and dateTo
        """
        loctime = getattr(self, "loctime", None)
        if loctime is None:
            td_title = getattr(self, "tdtitle", None)
            title_parts = td_title.split(",")
            del title_parts[0]
            loctime = ",".join(title_parts)
            loctime = loctime.strip(".")
            setattr(self, "loctime", loctime)
        if loctime is None:
            return None
        dateFrom, dateTo = self.extractDates(loctime)
        if dateFrom is not None:
            setattr(self, "dateFrom", dateFrom)
        if dateTo is not None:
            setattr(self, "dateTo", dateTo)
        self.extractAndSetLocation(locationStr=loctime)

    def extractAndSetLocation(self, locationStr:str) -> (str, str):
        """
        Extracts the location from the given string and returns the found city and country
        ToDo: Once the EventReferenceParser from cc is updated to support city country combinations switch to it
        Args:
            locationStr: string to extract the locations from

        Returns:
            city wikidata id, country wikidata id
        """
        parser = self.__class__.__dict__.get("locationparser")
        if parser is None:
            parser = LocationContext.fromCache()
            self.__class__.locationparser = parser
        locationStr = self.removePartsMatching(locationStr, pattern="\d")
        for month in calendar.month_name:
            if month == "":
                continue
            locationStr = locationStr.replace(month, " ")
        locations = parser.locateLocation(locationStr, verbose=True)
        locations = self.rankLocations(locationStr, locations)
        city = None
        cityWikidataId = None
        country = None
        countryWikidataId = None
        if locations is not None and len(locations) > 0:
            bestMatch = locations[0]
            if isinstance(bestMatch, City):
                city = bestMatch.name
                cityWikidataId = bestMatch.wikidataid
                country = bestMatch.country.name
                countryWikidataId = bestMatch.country.wikidataid
            elif isinstance(bestMatch, Country):
                country = bestMatch.wikidataid
        virtualEventKeywords = ["virtual", "online"]
        for keyword in virtualEventKeywords:
            if keyword in locationStr.lower():
                setattr(self, "virtualEvent", True)
        if city is not None:
            setattr(self, "city", city)
            setattr(self, "cityWikidataId", cityWikidataId)
        if countryWikidataId is not None:
            setattr(self, "country", country)
            setattr(self, "countryWikidataId", countryWikidataId)

    def extractDates(self, dateStr:str, durationThreshold: int = 11) -> (datetime.date, datetime.date):
        """"
        Extracts the start and end time from the given string
        optimized for the format of the loctime property
        Args:
            dateStr: string to extract the dates from
            durationThreshold: number of days allowed between two extracted dates
        """
        dateFrom = None
        dateTo = None
        if dateStr is None:
            return None, None
        # normalize certain foreign language month names that occur regularly
        if "novembro" in dateStr.lower():
            dateStr = dateStr.lower().replace("novembro", "november")
        loctimeParts = re.split("[,)(]", dateStr)
        if re.fullmatch("\d{4}", loctimeParts[-1].strip()):
            year = loctimeParts[-1].strip()
            rawDate = loctimeParts[-2].strip()
            if len(loctimeParts) >= 3:
                if loctimeParts[-3].lower().strip() in [cn.lower() for cn in calendar.month_name]:
                    rawDate = f"{loctimeParts[-3]} {rawDate}"
            dateParts: list = re.split("[-–‐&]| to | and ", rawDate)
            try:
                if len(dateParts) == 1:
                    dateFrom = dateutil.parser.parse(f"{dateParts[0]} {year}")
                    dateTo = dateFrom
                elif len(dateParts) == 2:
                    dateParts.sort(key=lambda r: len(r), reverse=True)
                    dateOne = dateutil.parser.parse(f"{dateParts[0]} {year}")
                    if len(dateParts[-1].strip()) <= 4:
                        dayMonthParts = dateParts[0].split(" ")
                        dayMonthParts.sort(key=lambda r: len(r), reverse=True)
                        endDate = dayMonthParts[0] + dateParts[1]
                        dateTwo = dateutil.parser.parse(f"{endDate} {year}")
                    else:
                        dateTwo = dateutil.parser.parse(f"{dateParts[1]} {year}")
                    dates = [dateOne, dateTwo]
                    dates.sort()
                    dateFrom = dates[0]
                    dateTo = dates[1]
            except:
                pass
            if dateTo is not None and dateFrom is not None:
                delta = dateTo - dateFrom
                if delta < datetime.timedelta():
                    print("Error this should not be possible")
                elif delta > datetime.timedelta(days=durationThreshold):
                    print(self.number, f"Event with a duration of more than {durationThreshold} days seems suspicious")
                else:
                    return dateFrom.date(), dateTo.date()
            else:
                print(self.number, dateStr, "→ Dates could not be extracted")
            return None, None
        else:
            # corner case
            return None, None

    @staticmethod
    def removePartsMatching(value:str, pattern:str, separator=','):
        """
        Removes parts from the given value matching the pattern
        """
        parts = value.split(separator)
        resParts = []
        for part in parts:
            if re.search(pattern, part) is None:
                resParts.append(part)
        resValue = separator.join(resParts)
        return resValue

    @staticmethod
    def rankLocations(locationStr:str, locations: typing.List[Location]):
        """
        rank the given locations to find the best match to the given location string
        Args:
            locationStr: location string
            locations: list of locations objects
        """
        rankedLocations = []
        for location in locations:
            locationsToCheck = []
            if isinstance(location, City):
                locationsToCheck = [location, location.region, location.country]
            elif isinstance(location, Region):
                locationsToCheck = [location, location.country]
            elif isinstance(location, Country):
                locationsToCheck = [location]
            score = 0
            for ltc in locationsToCheck:
                if ltc.name in locationStr:
                    score += 1
            rankedLocations.append((score, location))
        rankedLocations.sort(key=lambda scoreTuple: scoreTuple[0], reverse=True)
        return [location for score, location in rankedLocations]

    def __str__(self):
        text=f"Vol-{self.number}"
        return text

    @property
    def sessions(self):
        """
        sessions of this volume
        """
        return self._sessions

    @sessions.setter
    def sessions(self, session):
        # ToDo: Adjust to proper 1:n handling
        if hasattr(self, '_sessions') and isinstance(self._sessions, list):
            self._sessions.append(session)
        else:
            setattr(self, '_sessions', session)

    @property
    def papers(self):
        """
        papers of this volume
        """
        return
    
    def extractValuesFromVolumePage(self, timeout: float = 3)->typing.Tuple[dict,BeautifulSoup]:
        '''
        extract values from the given volume page
        '''
        self.desc="?"
        self.h1="?"
        if self.url is None:
            return None,None
        volumeParser = VolumeParser(timeout=timeout)
        parseDict,soup = volumeParser.parse_volume(self.getVolumeNumber())
        self.fromDict(parseDict)
        return parseDict,soup

    def getSubmittingEditor(self):
        """
        Returns the Editor that submitted the volume
        """
        submitter=None
        if hasattr(self, "editors"):
            for editor in self.editors:
                if isinstance(editor, Editor):
                    if getattr(editor, "submitted", False):
                        submitter=editor
                        break
        return submitter


class VolumeManager(EntityManager):
    """
    Contains multiple ceurws volumes
    """

    def __init__(self, tableName:str="volumes"):
        super(VolumeManager, self).__init__(listName="volumes",
                                            clazz=Volume,
                                            tableName=tableName,
                                            entityName=Volume.__class__.__name__,
                                            primaryKey="number",
                                            entityPluralName="volumes",
                                            config=CEURWS.CONFIG,
                                            name=self.__class__.__name__)


    def load(self):
        '''
        load the volumeManager
        '''
        if Download.needsDownload(CEURWS.CACHE_FILE):
            self.loadFromIndexHtml(force=True)
        else:
            self.loadFromBackup()
            
    def loadFromBackup(self):
        '''
        load from the SQLITE Cache file
        '''
        self.fromStore(cacheFile=CEURWS.CACHE_FILE)
        
    def recreate(self,progress:bool=False,limit=None):
        """
        recreate me by a full parse of all volume files
        
        Args:
            progress(bool): if True show progress
        """
        pm=PaperManager()
        paper_list=pm.getList()
        # first reload me from the main index
        self.loadFromIndexHtml(force=True)
        if progress:
            t=tqdm(total=len(self.volumes))
        else:
            t=None
        invalid=0
        for volume in self.volumes:
            _volume_record,soup=volume.extractValuesFromVolumePage()
            if soup:
                ptp=PaperTocParser(number=volume.number,soup=soup,debug=self.debug)
                paper_records=ptp.parsePapers()
                for paper_record in paper_records:
                    paper=Paper()
                    paper.fromDict(paper_record)
                    paper_list.append(paper)
            if not volume.valid:
                invalid+=1
            if t is not None and volume.valid:
                #print(f"{volume.url}:{volume.acronym}:{volume.desc}:{volume.h1}:{volume.title}")
                if volume.acronym:
                    description=volume.acronym[:20]
                else:
                    description="?"
                t.set_description(f"{description}")
                t.update()
        print(f"storing recreated volume table for {len(self.volumes)} volumes ({invalid} invalid)")
        self.store()
        print(f"storing {len(paper_list)} papers")
        pm.store()
        
    def loadFromIndexHtml(self,force:bool=False):
        '''
        load my content from the index.html file
        
        Args:
            force(bool): if TRUE fetch index.html from internet else read locally cached version
        '''
        htmlText=self.getIndexHtml(force=force)
        indexParser=IndexHtmlParser(htmlText,debug=self.debug)
        volumeRecords=indexParser.parse() 
        for volumeRecord in volumeRecords.values():
            volume=Volume()
            volume.fromDict(volumeRecord)
            for attr in ["desc","h1"]:
                if not hasattr(volume, attr):
                    setattr(volume, attr, "?")
            self.volumes.append(volume)
        
    def getIndexHtml(self,force:bool=False):
        '''
        get the index html
        '''
        cacheHtml=CEURWS.CACHE_HTML
        if os.path.isfile(cacheHtml) and not force:
            with open(cacheHtml, 'r') as file:
                html_page = file.read()
        else:
            req = Request(CEURWS.URL, headers={'User-Agent': 'pyCEURMake'})
            html_page = urlopen(req).read().decode()
            Path(CEURWS.CACHE_DIR).mkdir(parents=True, exist_ok=True)
            with open(cacheHtml, 'w') as htmlFile:
                print(html_page,file=htmlFile)
        return html_page

class Paper(JSONAble):
    """
    Represents a paper
    """

    @staticmethod
    def getSamples():
        samples=[
            {
                "id": "Vol-2436/s1/summary",  # id is constructed with volume and position → <volNumber>/s<position>/<type>_<position_relative_to_type>
                "type":"summary",
                "position": 0,
                "title": "1st Workshop on Evaluation and Experimental Design in Data Mining and Machine Learning (EDML 2019)",
                "pdf": "http://ceur-ws.org/Vol-2436/summary.pdf",
                "pagesFrom": 1,
                "pagesTo": 3,
                "authors": ["Eirini Ntoutsi", "Erich Schubert", "Arthur Zimek", "Albrecht Zimmermann"]
            },
            {
                "id": "Vol-2436/s1/invited_1",
                "type":"invited",
                "position": 1,
                "title": "Evaluation of Unsupervised Learning Results: Making the Seemingly Impossible Possible",
                "pdf": "http://ceur-ws.org/Vol-2436/invited_1.pdf",
                "pagesFrom": 4,
                "pagesTo": 4,
                "authors": ["Ricardo J. G. B. Campello"]
            },
            {
                "id": "Vol-2436/s1/article_1",
                "type": "article",
                "position": 2,
                "title": "EvalNE: A Framework for Evaluating Network Embeddings on Link Prediction",
                "pdf": "http://ceur-ws.org/Vol-2436/article_2.pdf",
                "pagesFrom": 5,
                "pagesTo": 13,
                "authors": ["Alexandru Mara", "Jefrey Lijffijt", "Tijl De Bie"]
            }
        ]
        
    def __str__(self):
        """
        return my string representation
        
        Returns:
            str: my text representation
        """
        text=self.title
        return text


class PaperManager(EntityManager):
    """
    Contains multiple ceurws papers
    """

    def __init__(self):
        super(PaperManager, self).__init__(listName="papers",
                                            clazz=Paper,
                                            tableName="papers",
                                            entityName=Paper.__class__.__name__,
                                            primaryKey="id",
                                            entityPluralName="papers",
                                            config=CEURWS.CONFIG,
                                            handleInvalidListTypes=True,
                                            listSeparator=",",
                                            name=self.__class__.__name__)


class Session(JSONAble):
    """
    Represents a session in ceur-ws
    """

    def getSamples(self):
        samples=[
            {
                "id":"Vol-2436/s1",  # id is constructed with volume and position → <volNumber>/s<position>
                "volume":{"Vol-2436": Volume},  # n:1 relation / reporting chain
                "title":"Information Technologies and Intelligent Decision Making Systems II",
                "position": 1,
                "papers": {   # 1:n relation / command chain
                    "VOL-2436/s1/p1":Paper,
                    "VOL-2436/s1/p2":Paper
                }
            }
        ]

    @property
    def volume(self)->Volume:
        if self._volume is None and self._volumeKey is not None:
                # load volume
                lVolume="ToDo:"
                # set volume
                self._volume=lVolume
                pass
        else:
            return self._volume


    @property
    def papers(self, cached:bool=False): #dict: str→Paper
        if cached:
            # check if cached
            pass
        else:
            #load papers
            if cached:
                #set papers
                pass
        return self._papers

    @papers.setter
    def papers(self, paper:Paper):
        # ToDo: Adjust to proper 1:n handling
        if hasattr(self, '_papers') and isinstance(self._papers, dict):
            self._papers.update(paper.id, paper)
        else:
            setattr(self,'_papers',paper)



class SessionManager(EntityManager):
    """
    Contains multiple ceurws sessions
    """

    def __init__(self):
        super(SessionManager, self).__init__(listName="sessions",
                                            clazz=Session,
                                            tableName="sessions",
                                            entityName=Session.__class__.__name__,
                                            primaryKey="id",  #ToDo: check if just the title is a sufficent key or if an ID must be added
                                            entityPluralName="sessions",
                                            config=CEURWS.CONFIG,
                                            name=self.__class__.__name__)



class Editor(JSONAble):
    """
    Represents a volume editor
    """

    @staticmethod
    def getSamples():
        samples=[
            {
                "id": "Vol-2436/John Doe",
                "name": "John Doe",
                "homepage": "http://www.example.org/john",
                "country": "Germany",
                "affiliation": "Leibniz University Hannover & L3S Research Center",
                "submitted": False
            },
            {
                "id": "Vol-2436/Jane Doe",
                "name": "Jane Doe",
                "homepage": "http://www.example.org/jane",
                "country": "Germany",
                "affiliation": "Technical University Dortmund",
                "submitted": True
            }
        ]


class EditorManager(EntityManager):
    """
    Contains multiple ceurws editors
    """

    def __init__(self):
        super(EditorManager, self).__init__(listName="editors",
                                            clazz=Editor,
                                            tableName="editors",
                                            entityName=Session.__class__.__name__,
                                            primaryKey="id",
                                            entityPluralName="editors",
                                            config=CEURWS.CONFIG,
                                            name=self.__class__.__name__)


class Conference(JSONAble):
    """
    Represents a conference
    """

    @staticmethod
    def getSamples():
        samples=[
            {
                "id": "Vol-2436",
                "fullTitle": "SIAM International Conference on Data Mining",
                "homepage": "https://www.siam.org/Conferences/CM/Main/sdm19",
                "acronym": "SDM 2019"
            }
        ]


class ConferenceManager(EntityManager):
    """
    Contains multiple ceurws sessions
    """

    def __init__(self):
        super(ConferenceManager, self).__init__(listName="conferences",
                                            clazz=Conference,
                                            tableName="conferences",
                                            entityName=Conference.__class__.__name__,
                                            primaryKey="id",
                                            entityPluralName="conferences",
                                            config=CEURWS.CONFIG,
                                            name=self.__class__.__name__)

