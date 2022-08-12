import datetime
import os

from lodstorage.entity import EntityManager
from lodstorage.jsonable import JSONAble
from lodstorage.storageconfig import StorageConfig
#from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
from pathlib import Path
#from lxml import etree
from ceurws.indexparser import IndexHtmlParser

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
                "sessions":[Session]
            }
        ]
        return samples
    
    def __str__(self):
        text=f"Vol-{self.number}"
        return text

    @property
    def year(self):
        if hasattr(self, "date") and isinstance(self.date, datetime.datetime):
            return self.date.year

    @property
    def volNumber(self)->str:
        if hasattr(self, "number") and self.number:
            return f"Vol-{self.number}"
        return None

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

    def getSubmittingEditor(self):
        """
        Retruns the Editor that sumbitted the volume
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


    def loadFromBackup(self):
        self.fromStore(cacheFile=CEURWS.CACHE_FILE)
        
    def loadFromIndexHtml(self,force:bool=False):
        '''
        load my content from the index.html file
        '''
        htmlText=self.getIndexHtml(force=force)
        indexParser=IndexHtmlParser(htmlText,debug=self.debug)
        volumeRecords=indexParser.parse() 
        for volumeRecord in volumeRecords.values():
            volume=Volume()
            volume.fromDict(volumeRecord)
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
    Represents a conference
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


class PaperManager(EntityManager):
    """
    Contains multiple ceurws sessions
    """

    def __init__(self):
        super(PaperManager, self).__init__(listName="papers",
                                            clazz=Editor,
                                            tableName="papers",
                                            entityName=Session.__class__.__name__,
                                            primaryKey="id",
                                            entityPluralName="papers",
                                            config=CEURWS.CONFIG,
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
    Contains multiple ceurws sessions
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
                                            clazz=Editor,
                                            tableName="conferences",
                                            entityName=Session.__class__.__name__,
                                            primaryKey="id",
                                            entityPluralName="conferences",
                                            config=CEURWS.CONFIG,
                                            name=self.__class__.__name__)

if __name__ == '__main__':
    manager=VolumeManager()
    try:
        manager.loadFromBackup()
        for volume in manager.getList():
            print(volume)
    except Exception as ex:
        print(ex)