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
        
    def getSampleVolume(self):
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

    def test_resolveLoctime(self):
        """tests resolveLoctime"""
        test_params = [
            ("Moscow, Russia, July 18, 2016", "2016-07-18", "2016-07-18", "Q649", "Q159"),
            ("Halifax, Canada, July 13-16, 2016", "2016-07-13", "2016-07-16", "Q2141", "Q16"),
            # ("Genoa (Italy) February 10-11, 2011", "2011-02-10", "2011-02-11", "Q1449", "Q38"),
            ("Berlin, Germany, June 30 & July 1, 2011", "2011-06-30", "2011-07-01", "Q64", "Q183"),
            ("La Clusaz, France, 30-31 March, 2011", "2011-03-30", "2011-03-31", "Q530721", "Q142"),
            ("Opole, Poland, 13-17 August, 2012", "2012-08-13", "2012-08-17", "Q92212", "Q36"),
            ("Cuiabá, Mato Grosso, Brasil, Novembro 05, 2012", "2012-11-05", "2012-11-05", "Q170762", "Q155"),
            ("Paphos, Cyprus, September, 21, 2013", "2013-09-21", "2013-09-21", "Q180918", "Q229"),
            ("Rio de Janeiro, Brazil, August 28th to 30th, 2013", "2013-08-28", "2013-08-30", "Q8678", "Q155"),
            # ("Cazalla de la Sierra, España, 12 y 13 de Junio, 2014", "2014-06-12", "2014-06-13", "Q1445283", "Q29"),
            ("Annecy, France, July 6–9, 2016", "2016-07-06", "2016-07-09", "Q50189", "Q142"),
            ("Lisbon, Portugal, October 11, 2010", "2010-10-11", "2010-10-11", "Q597", "Q45"),
            ("Rende, Italy, November 19‐20, 2019", "2019-11-19", "2019-11-20", "Q53946", "Q38"),
            ("Online, September, 14 & 15, 2020", "2020-09-14", "2020-09-15", None, None),
            ("Düsseldorf, Germany, September 28-29, 2009", "2009-09-28", "2009-09-29", "Q1718", "Q183"),
            ("Chicago, USA, October 23th and 26th, 2011", "2011-10-23", "2011-10-26", "Q1297", "Q30"),
            ("Oum El Bouaghi, Algeria, May 25 and 26, 2021", "2021-05-25", "2021-05-26", "Q5478122", "Q262"),
            ("Hersonissos, Greece, May 30th, 2022", "2022-05-30", "2022-05-30", "Q1018106", "Q41"),
            ("Arequipa, Peru, November 08-10, 2022", "2022-11-08", "2022-11-10", "Q159273", "Q419"),
            # ("Seattle, USA, 18th-23rd September 2022", "2022-09-18", "2022-09-23", "Q5083", "Q30")  # corner case of date definition
            # ("Windsor, United Kingdom, September 20-30th, 2022", "2022-09-20", "2022-09-30", "Q464955", "Q145")  # City missing in geograpy3
        ]
        for param in test_params:
            with self.subTest("Tests resolveLoctime on", param=param):
                loctime, expectedDateFrom, expectedDateTo, expectedCity, expectedCountry = param
                vol = Volume()
                vol.fromDict({"number": 1, "loctime": loctime})
                vol.resolveLoctime()
                self.assertEqual(datetime.datetime.fromisoformat(expectedDateFrom).date(), getattr(vol, "dateFrom"))
                self.assertEqual(datetime.datetime.fromisoformat(expectedDateTo).date(), getattr(vol, "dateTo"))
                self.assertEqual(expectedCity, getattr(vol, "cityWikidataId", None))
                self.assertEqual(expectedCountry, getattr(vol, "countryWikidataId",None))

    def test_resolveLoctime_virtual_events(self):
        """
        test extraction of virtual event information
        """
        test_params = [

        ]
        for param in test_params:
            with self.subTest("Tests resolveLoctime on", param=param):
                loctime, expectedDateFrom, expectedDateTo, expectedCity, expectedCountry = param

    def test_locationExtraction(self):
        """
        tests locationExtraction
        """
        test_params=[
            ("Online, September, 14 & 15, 2020", True),
            ("Waterloo, Sierra Leone", False),
            ("Virtual Event, Pescara, Italy, September 12, 2022", True)
        ]
        for param in test_params:
            with self.subTest("Tests resolveLoctime on", param=param):
                locStr, is_virtual_event = param
                vol = Volume()
                vol.extractAndSetLocation(locationStr=locStr)
                self.assertEqual(is_virtual_event, vol.isVirtualEvent())

    def test_removePartsMatching(self):
        """
        tests removePartsMatching
        """
        test_params = [# input, pattern, expected
            ("Moscow, Russia, July 18, 2016", "\d", "Moscow, Russia"),
            ("Berlin, Germany, June 30 & July 1, 2011", "[a-zA-Z]", " 2011"),
            ("Berlin, Germany, June 30 & July 1, 2011", "\d", "Berlin, Germany")
        ]
        for param in test_params:
            with self.subTest("Tests removePartsMatching on", param=param):
                value, pattern, expectedResult = param
                actualResult = Volume.removePartsMatching(value, pattern=pattern)
                self.assertEqual(expectedResult, actualResult)