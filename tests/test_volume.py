import datetime
import os
from unittest import TestCase

from jinja2 import Environment, PackageLoader, select_autoescape, FileSystemLoader

from ceurws.ceurws import Conference, Editor, Session, Paper, Volume
from ceurws.ceurws import SessionManager
import getpass

class TestSessions(TestCase):
    """
    Test session manager
    """

    def test_sessions(self):
        if getpass.getuser() != "holzheim":
            # switch on for CI
            return
        sessions=[
            {"volume":2992, "title":"Information Technologies and Intelligent Decision Making Systems II"},
            {"volume":2976, "title": "Digital Infrastructures for Scholarly Content Objects 2021"},
            {"volume":2975, "title": "Novel Approaches with AI and Edge Computing"},  #http://ceur-ws.org/Vol-2975/
            {"volume":2975, "title": "Impact, Metrics and Sustainability"},  #http://ceur-ws.org/Vol-2975/
        ]
        manager=SessionManager()
        manager.fromLoD(sessions)
        manager.store()


class TestVolume(TestCase):
    """
    Test volume manager
    """

    def setUp(self) -> None:
        scriptdir = os.path.dirname(os.path.abspath(__file__))
        template_folder = scriptdir + '/../ceurws/resources/templates'
        self.env = Environment(
            loader=FileSystemLoader(searchpath=template_folder),
            autoescape=select_autoescape(['html', 'xml'])
        )
        self.env.globals['datetime']=datetime.datetime
        self.env.globals['enumerate']=enumerate
        self.env.globals['len'] = len

    def test_volumes(self):
        """
        tests the rendering of a volume as volume_index.html
        """
        conference=Conference()
        conference.fromDict({
            "id": "Vol-2436",
            "fullTitle": "SIAM International Conference on Data Mining",
            "homepage": "https://www.siam.org/Conferences/CM/Main/sdm19",
            "acronym": "SDM 2019"
        })
        editor=Editor()
        editor.fromDict({
            "id": "Vol-2436/Jane Doe",
            "name": "Jane Doe",
            "homepage": "http://www.example.org/jane",
            "country": "Germany",
            "affiliation": "Technical University Dortmund",
            "submitted": True
        })
        paper1=Paper()
        paper1.fromDict({
            "id": "Vol-2436/s1/invited_1",
            "type": "invited",
            "position": 1,
            "title": "Evaluation of Unsupervised Learning Results: Making the Seemingly Impossible Possible",
            "pdf": "http://ceur-ws.org/Vol-2436/invited_1.pdf",
            "pagesFrom": 4,
            "pagesTo": 4,
            "authors": ["Ricardo J. G. B. Campello"]
        })
        session=Session()
        session.fromDict({
            "id": "Vol-2436/s1",  # id is constructed with volume and position → <volNumber>/s<position>
            "title": "Information Technologies and Intelligent Decision Making Systems II",
            "position": 1,
            "papers": {  # 1:n relation / command chain
                "VOL-2436/s1/p1": paper1
            }
        })
        volume=Volume()
        volume.fromDict(
            {
                # Keys/Identifiers
                "number": 2436,
                "acronym": "EDML 2019",
                # Relations
                "conference": conference,
                "editors": [editor],
                "sessions": [session],
                # Properties
                "url": "http://ceur-ws.org/Vol-2436/",
                "title": "Evaluation and Experimental Design in Data Mining and Machine Learning",
                "fullTitle": "1st Workshop on Evaluation and Experimental Design in Data Mining and Machine Learning",
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
                "submitDate": "2019-07-28"
            }
        )

        template = self.env.get_template('volume_index.jinja')
        print(template.render(volume=volume))