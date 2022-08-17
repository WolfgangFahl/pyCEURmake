import datetime
from tests.basetest import Basetest
from ceurws.ceur_ws import Conference, Editor, Session,  Paper, Volume, VolumeManager
from ceurws.template import TemplateEnv


class TestVolume(Basetest):
    """
    Test volume manager
    """

    def setUp(self,debug=False,profile=True) -> None:
        Basetest.setUp(self, debug, profile)
        self.templateEnv=TemplateEnv()
        self.vm=VolumeManager()
        self.vm.load()
        
    def getSampleVolum(self):
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
    
    def testVolumeTemplate(self):
        """
        tests the rendering of a volume as volume_index.html
        """
        template=self.templateEnv.getTemplate('volume_index_body.html')
        vol3000=self.vm.getList()[3000]
        for volume in [self.getSampleVolum(),vol3000]:
            html=template.render(volume=volume)
            debug=self.debug
            #debug=True
            if debug:
                print(html)