import calendar
import datetime
import os
import re
from pathlib import Path
from typing import Optional, Union
from urllib.request import Request, urlopen

import dateutil.parser
from bs4 import BeautifulSoup
from geograpy.locator import City, Country, Location, LocationContext, Region
from lodstorage.entity import EntityManager
from lodstorage.jsonable import JSONAble
from lodstorage.storageconfig import StorageConfig

from ceurws.indexparser import IndexHtmlParser, ParserConfig
from ceurws.loctime import LoctimeParser
from ceurws.papertocparser import PaperTocParser
from ceurws.utils.download import Download
from ceurws.volumeparser import VolumeParser


class CEURWS:
    """
    CEUR-WS
    """

    URL = "http://ceur-ws.org"
    home = str(Path.home())
    CACHE_DIR = "%s/.ceurws" % home
    CACHE_FILE = f"{CACHE_DIR}/ceurws.db"
    CACHE_HTML = f"{CACHE_DIR}/index.html"
    CONFIG = StorageConfig(cacheFile=CACHE_FILE)


class Volume(JSONAble):
    """
    Represents a volume in ceur-ws
    """

    def __init__(
        self,
        number: Optional[int] = None,
        url: Optional[str] = None,
        title: Optional[str] = None,
        fullTitle: Optional[str] = None,
        acronym: Optional[str] = None,
        lang: Optional[str] = None,
        location: Optional[str] = None,
        country: Optional[str] = None,
        countryWikidataId: Optional[str] = None,
        region: Optional[str] = None,
        city: Optional[str] = None,
        cityWikidataId: Optional[str] = None,
        ordinal: Optional[int] = None,
        date: Optional[datetime.datetime] = None,
        dateFrom: Optional[datetime.datetime] = None,
        dateTo: Optional[datetime.datetime] = None,
        pubYear: Optional[str] = None,
        pubDate: Optional[datetime.datetime] = None,
        submitDate: Optional[datetime.datetime] = None,
        valid: bool = True,
        conference: Optional["Conference"] = None,
        editors: Optional[list["Editor"]] = None,
        sessions: Optional[list["Session"]] = None,
        virtualEvent: bool = False,
        submittedBy: Optional[str] = None,
    ):
        """
        constructor
        """
        self.number = number
        self.url = url
        self.title = title
        self.fullTitle = fullTitle
        self.acronym = acronym
        self.lang = lang
        self.location = location
        self.country = country
        self.countryWikidataId = countryWikidataId
        self.region = region
        self.city = city
        self.cityWikidataId = cityWikidataId
        self.ordinal = ordinal
        self.date = date
        self.dateFrom = dateFrom
        self.dateTo = dateTo
        self.pubYear = pubYear
        self.pubDate = pubDate
        self.submitDate = submitDate
        self.valid = valid
        self.conference = conference
        self.editors = editors
        self.sessions = sessions
        self.virtualEvent = virtualEvent
        self.submittedBy = submittedBy

    def getSamples(self):
        samples = [
            {
                "number": 2436,
                "url": "http://ceur-ws.org/Vol-2436/",
                "title": "Evaluation and Experimental Design in Data Mining and Machine Learning",
                "fullTitle": "1st Workshop on Evaluation and Experimental Design in Data Mining and Machine Learning",
                "acronym": "EDML 2019",
                "lang": "en",
                "location": "Calgary, Alberta, Canada",
                "country": "Canada",
                "region": "Alberta",
                "city": "Calgary",
                "ordinal": 1,
                "date": datetime.datetime(year=2019, month=5, day=4),
                "dateFrom": "",
                "dateTo": "",
                "pubYear": 2019,
                "pubDate": "2019-09-08",
                "submitDate": "2019-07-28",
                "valid": True,
                "conference": Conference,
                "editors": [Editor],
                "sessions": [Session],
                "virtualEvent": False,
            }
        ]
        return samples

    def getVolumeNumber(self):
        """
        get number of the volume
        """
        number = getattr(self, "number", "Volume has no number")
        return number

    def getVolumeUrl(self) -> Union[str, None]:
        """
        get the url of the volume page
        """
        number = getattr(self, "number", None)
        url = self.getVolumeUrlOf(number)
        return url

    @staticmethod
    def getVolumeUrlOf(
        number: Union[str, int],
    ) -> Union[str, None]:
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

    def get_loctime(self) -> str:
        """
        get the loctime
        """
        loctime = getattr(self, "loctime", None)
        if loctime is None:
            td_title = getattr(self, "tdtitle", None)
            if td_title:
                title_parts = td_title.split(",")
                del title_parts[0]
                loctime = ",".join(title_parts)
                loctime = loctime.strip(".")
                self.loctime = loctime
            else:
                pass
        return loctime

    def resolveLoctime(self):
        """
        Resolve the loctime property by breaking it down to city, region, country, dateFrom, and dateTo
        """
        loctime = self.get_loctime()
        if loctime is None:
            return None
        dateFrom, dateTo = self.extractDates(loctime)
        if dateFrom is not None:
            self.dateFrom = dateFrom
        if dateTo is not None:
            self.dateTo = dateTo
        self.extractAndSetLocation(locationStr=loctime)

    def extractAndSetLocation(self, locationStr: str) -> (str, str):
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
                self.virtualEvent = True
        if city is not None:
            self.city = city
            self.cityWikidataId = cityWikidataId
        if countryWikidataId is not None:
            self.country = country
            self.countryWikidataId = countryWikidataId

    def extractDates(self, dateStr: str, durationThreshold: int = 11) -> (datetime.date, datetime.date):
        """ "
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
            if len(loctimeParts) >= 3 and loctimeParts[-3].lower().strip() in [
                cn.lower() for cn in calendar.month_name
            ]:
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
            except Exception:
                pass
            if dateTo is not None and dateFrom is not None:
                delta = dateTo - dateFrom
                if delta < datetime.timedelta():
                    print("Error this should not be possible")
                elif delta > datetime.timedelta(days=durationThreshold):
                    print(
                        self.number,
                        f"Event with a duration of more than {durationThreshold} days seems suspicious",
                    )
                else:
                    return dateFrom.date(), dateTo.date()
            else:
                print(self.number, dateStr, "→ Dates could not be extracted")
            return None, None
        else:
            # corner case
            return None, None

    @staticmethod
    def removePartsMatching(value: str, pattern: str, separator=","):
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
    def rankLocations(locationStr: str, locations: list[Location]):
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
                locationsToCheck = [
                    location,
                    location.region,
                    location.country,
                ]
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
        text = f"Vol-{self.number}"
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
        if hasattr(self, "_sessions") and isinstance(self._sessions, list):
            self._sessions.append(session)
        else:
            self._sessions = session

    @property
    def papers(self):
        """
        papers of this volume
        """
        return

    def extractValuesFromVolumePage(self, timeout: float = 3) -> tuple[dict, BeautifulSoup]:
        """
        extract values from the given volume page
        """
        self.desc = "?"
        self.h1 = "?"
        if self.url is None:
            return None, None
        volumeParser = VolumeParser(timeout=timeout)
        parseDict, soup = volumeParser.parse_volume(self.getVolumeNumber())
        self.fromDict(parseDict)
        return parseDict, soup

    def getSubmittingEditor(self):
        """
        Returns the Editor that submitted the volume
        """
        submitter = None
        if hasattr(self, "editors"):
            for editor in self.editors:
                if isinstance(editor, Editor) and getattr(editor, "submitted", False):
                    submitter = editor
                    break
        return submitter


class VolumeManager(EntityManager):
    """
    Contains multiple ceurws volumes
    """

    def __init__(self, tableName: str = "volumes"):
        super().__init__(
            listName="volumes",
            clazz=Volume,
            tableName=tableName,
            entityName=Volume.__class__.__name__,
            primaryKey="number",
            entityPluralName="volumes",
            config=CEURWS.CONFIG,
            handleInvalidListTypes=True,
            name=self.__class__.__name__,
        )

    def load(self):
        """
        load the volumeManager
        """
        if Download.needsDownload(CEURWS.CACHE_FILE):
            self.loadFromIndexHtml()
            self.store()
        else:
            self.loadFromBackup()

    def loadFromBackup(self):
        """
        load from the SQLITE Cache file
        """
        self.fromStore(cacheFile=CEURWS.CACHE_FILE)

    def update(self, parser_config: ParserConfig):
        """
        update me by a checking for recently added volumes
        """
        self.set_down_to_volume(parser_config)
        self.update_or_recreate(parser_config)

    def set_down_to_volume(self, parser_config):
        volumeCount = len(self.volumes)
        if volumeCount > 0:
            max_vol = self.volumes[-1]
            parser_config.down_to_volume = max_vol.number + 1
        else:
            pass

    def recreate(self, parser_config: ParserConfig):
        """
        recreate me by a full parse of all volume files
        """

        self.update_or_recreate(parser_config)

    def update_or_recreate(self, parser_config: ParserConfig):
        """
        recreate or update me by parsing the index.html file

        Args:
            progress(bool): if True show progress
            down_to_volume(int): the volume number to parse down to
        """
        progress_bar = parser_config.progress_bar
        loctime_parser = LoctimeParser()
        pm = PaperManager()
        if parser_config.down_to_volume != 1:
            pm.fromStore(cacheFile=CEURWS.CACHE_FILE)
        paper_list = pm.getList()

        # first reload me from the main index
        self.loadFromIndexHtml(parser_config)
        invalid = 0
        for volume in self.volumes:
            if volume.number < parser_config.down_to_volume:
                break
            _volume_record, soup = volume.extractValuesFromVolumePage()
            if soup:
                ptp = PaperTocParser(number=volume.number, soup=soup, debug=self.debug)
                paper_records = ptp.parsePapers()
                for paper_record in paper_records:
                    paper = Paper()
                    paper.fromDict(paper_record)
                    paper_list.append(paper)
            if not volume.valid:
                invalid += 1
            else:
                loctime = volume.get_loctime()
                if loctime:
                    loc_time_dict = loctime_parser.parse(loctime)
                    for key, value in loc_time_dict.items():
                        attr = f"loc_{key}"
                        setattr(volume, attr, value)
                    volume.resolveLoctime()
            # update progress bar
            if progress_bar:
                if volume.valid:
                    # print(f"{volume.url}:{volume.acronym}:{volume.desc}:{volume.h1}:{volume.title}")
                    description = volume.acronym[:20] if volume.acronym else "?"
                    progress_bar.set_description(f"{description}")
                progress_bar.update()
        print(f"storing recreated volume table for {len(self.volumes)} volumes ({invalid} invalid)")
        self.store()
        print(f"storing {len(paper_list)} papers")
        pm.store()

    def loadFromIndexHtml(self, parser_config: ParserConfig = None):
        """
        load my content from the index.html file

        Args:
            parser_config(ParserConfig): the parser Configuration to use
        """
        force = parser_config.force_download if parser_config else True
        htmlText = self.getIndexHtml(force)
        indexParser = IndexHtmlParser(htmlText, parser_config)
        volumeRecords = indexParser.parse()
        for volumeRecord in volumeRecords.values():
            volume = Volume()
            volume.fromDict(volumeRecord)
            for attr in ["desc", "h1"]:
                if not hasattr(volume, attr):
                    setattr(volume, attr, "?")
            self.volumes.append(volume)

    def getIndexHtml(self, force: bool = False):
        """
        get the index html
        """
        cacheHtml = CEURWS.CACHE_HTML
        if os.path.isfile(cacheHtml) and not force:
            with open(cacheHtml) as file:
                html_page = file.read()
        else:
            req = Request(CEURWS.URL, headers={"User-Agent": "pyCEURMake"})
            html_page = urlopen(req).read().decode()
            Path(CEURWS.CACHE_DIR).mkdir(parents=True, exist_ok=True)
            with open(cacheHtml, "w") as htmlFile:
                print(html_page, file=htmlFile)
        return html_page


class Paper(JSONAble):
    """
    Represents a paper
    """

    @staticmethod
    def getSamples() -> list[dict]:
        """
        get sample records of the entity
        """
        samples = [
            {
                # id is constructed with volume and position
                # → <volNumber>/s<position>/<type>_<position_relative_to_type>
                "id": "Vol-2436/s1/summary",
                "type": "summary",
                "position": 0,
                "title": "1st Workshop on Evaluation and Experimental Design in Data Mining and "
                "Machine Learning (EDML 2019)",
                "pdf": "http://ceur-ws.org/Vol-2436/summary.pdf",
                "pagesFrom": 1,
                "pagesTo": 3,
                "authors": [
                    "Eirini Ntoutsi",
                    "Erich Schubert",
                    "Arthur Zimek",
                    "Albrecht Zimmermann",
                ],
            },
            {
                "id": "Vol-2436/s1/invited_1",
                "type": "invited",
                "position": 1,
                "title": "Evaluation of Unsupervised Learning Results: Making the Seemingly Impossible Possible",
                "pdf": "http://ceur-ws.org/Vol-2436/invited_1.pdf",
                "pagesFrom": 4,
                "pagesTo": 4,
                "authors": ["Ricardo J. G. B. Campello"],
            },
            {
                "id": "Vol-2436/s1/article_1",
                "type": "article",
                "position": 2,
                "title": "EvalNE: A Framework for Evaluating Network Embeddings on Link Prediction",
                "pdf": "http://ceur-ws.org/Vol-2436/article_2.pdf",
                "pagesFrom": 5,
                "pagesTo": 13,
                "authors": [
                    "Alexandru Mara",
                    "Jefrey Lijffijt",
                    "Tijl De Bie",
                ],
            },
        ]
        return samples

    def __str__(self):
        """
        return my string representation

        Returns:
            str: my text representation
        """
        text = self.title
        return text


class PaperManager(EntityManager):
    """
    Contains multiple ceurws papers
    """

    def __init__(self):
        super().__init__(
            listName="papers",
            clazz=Paper,
            tableName="papers",
            entityName=Paper.__class__.__name__,
            primaryKey="id",
            entityPluralName="papers",
            config=CEURWS.CONFIG,
            handleInvalidListTypes=True,
            listSeparator=",",
            name=self.__class__.__name__,
        )


class Session(JSONAble):
    """
    Represents a session in ceur-ws
    """

    @staticmethod
    def getSamples() -> list[dict]:
        """
        get sample records of the entity
        """
        samples = [
            {
                "id": "Vol-2436/s1",  # id is constructed with volume and position → <volNumber>/s<position>
                "volume": {"Vol-2436": Volume},  # n:1 relation / reporting chain
                "title": "Information Technologies and Intelligent Decision Making Systems II",
                "position": 1,
                "papers": {  # 1:n relation / command chain
                    "VOL-2436/s1/p1": Paper,
                    "VOL-2436/s1/p2": Paper,
                },
            }
        ]
        return samples

    @property
    def volume(self) -> Volume:
        if self._volume is None and self._volumeKey is not None:
            # load volume
            lVolume = "ToDo:"
            # set volume
            self._volume = lVolume
            pass
        else:
            return self._volume

    @property
    def papers(self, cached: bool = False):  # dict: str→Paper
        if cached:
            # check if cached
            pass
        else:
            # load papers
            if cached:
                # set papers
                pass
        return self._papers

    @papers.setter
    def papers(self, paper: Paper):
        # ToDo: Adjust to proper 1:n handling
        if hasattr(self, "_papers") and isinstance(self._papers, dict):
            self._papers.update(paper.id, paper)
        else:
            self._papers = paper


class SessionManager(EntityManager):
    """
    Contains multiple ceurws sessions
    """

    def __init__(self):
        super().__init__(
            listName="sessions",
            clazz=Session,
            tableName="sessions",
            entityName=Session.__class__.__name__,
            primaryKey="id",  # ToDo: check if just the title is a sufficent key or if an ID must be added
            entityPluralName="sessions",
            config=CEURWS.CONFIG,
            name=self.__class__.__name__,
        )


class Editor(JSONAble):
    """
    Represents a volume editor
    """

    @staticmethod
    def getSamples() -> list[dict]:
        """
        get sample records of the entity
        """
        samples = [
            {
                "id": "Vol-2436/John Doe",
                "name": "John Doe",
                "homepage": "http://www.example.org/john",
                "country": "Germany",
                "affiliation": "Leibniz University Hannover & L3S Research Center",
                "submitted": False,
            },
            {
                "id": "Vol-2436/Jane Doe",
                "name": "Jane Doe",
                "homepage": "http://www.example.org/jane",
                "country": "Germany",
                "affiliation": "Technical University Dortmund",
                "submitted": True,
            },
        ]
        return samples


class EditorManager(EntityManager):
    """
    Contains multiple ceurws editors
    """

    def __init__(self):
        super().__init__(
            listName="editors",
            clazz=Editor,
            tableName="editors",
            entityName=Session.__class__.__name__,
            primaryKey="id",
            entityPluralName="editors",
            config=CEURWS.CONFIG,
            name=self.__class__.__name__,
        )


class Conference(JSONAble):
    """
    Represents a conference
    """

    @staticmethod
    def getSamples() -> list[dict]:
        """
        get sample records of the entity
        """
        samples = [
            {
                "id": "Vol-2436",
                "fullTitle": "SIAM International Conference on Data Mining",
                "homepage": "https://www.siam.org/Conferences/CM/Main/sdm19",
                "acronym": "SDM 2019",
            }
        ]
        return samples


class ConferenceManager(EntityManager):
    """
    Contains multiple ceurws sessions
    """

    def __init__(self):
        super().__init__(
            listName="conferences",
            clazz=Conference,
            tableName="conferences",
            entityName=Conference.__class__.__name__,
            primaryKey="id",
            entityPluralName="conferences",
            config=CEURWS.CONFIG,
            name=self.__class__.__name__,
        )
