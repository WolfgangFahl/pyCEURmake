"""
Created on 2024-03-09

@author: wf
"""
from ceurws.models.dblp import DblpScholar
from ceurws.dblp import DblpEndpoint, DblpAuthorIdentifier
from tests.basetest import Basetest
import os
import shutil
from tqdm import tqdm

class TestDblpEndpoint(Basetest):
    """tests DblpEndpoint"""
    
    @classmethod
    def setUpClass(cls)->None:
        super(TestDblpEndpoint, cls).setUpClass()
        cls.rm_dir("/tmp/.ceurws")
        
    @classmethod
    def rm_dir(self,directory: str):
        """
        Recursively removes all files and directories within the specified directory.
    
        Args:
            directory (str): The path to the directory from which files and directories will be removed.
    
        """
        for root, dirs, files in os.walk(directory, topdown=False):
            for name in files:
                os.unlink(os.path.join(root, name))
            for name in dirs:
                shutil.rmtree(os.path.join(root, name))
        

    def setUp(self, debug=True, profile=True):
        """
        override Basetest.setUp
        """
        super().setUp(debug, profile)
        self.endpointUrl = "http://dblp.wikidata.dbis.rwth-aachen.de/api/dblp"
        self.dblpEndpoint = DblpEndpoint(self.endpointUrl,debug=self.debug)
        # force cache refresh
        self.dblpEndpoint.cache_manager.base_dir="/tmp" 
        if not self.inPublicCI():
            self.dblpEndpoint.progress_bar=tqdm(total=100) # expected 36 secs = 100%    
      
    #@unittest.skipIf(Basetest.inPublicCI(), "queries unreliable dblp endpoint")
    def test_getWikidataIdByVolumeNumber(self):
        """tests getWikidataIdByVolumeNumber"""
        test_params = [
            ("1", ["conf/krdb/94"]),
            ("2400", ["conf/sebd/2019"]),
            ("-1", []),
            (3100, ["conf/psychobit/2021"]),
        ]
        for param in test_params:
            with self.subTest("test wikidata id query by volume number", param=param):
                number, expected = param
                actual = self.dblpEndpoint.getDblpIdByVolumeNumber(number)
                self.assertListEqual(expected, actual)

    #@unittest.skipIf(Basetest.inPublicCI(), "queries unreliable dblp endpoint")
    def test_convertEntityIdToUrlId(self):
        """tests convertEntityIdToUrlId"""
        test_params = [
            ("conf/aaai/2022", "conf/aaai/aaai2022"),
            ("conf/aaai", None),
            ("conf/aaai/aaai2022", None),
            ("", None),
            (None, None),
        ]
        for param in test_params:
            with self.subTest("test dblp id conversion", param=param):
                entityId, expected = param
                actual = self.dblpEndpoint.convertEntityIdToUrlId(entityId)
                self.assertEqual(expected, actual)

    # @unittest.skipIf(Basetest.inPublicCI(), "queries unreliable dblp endpoint")
    def test_toDblpUrl(self):
        """tests toDblpUrl"""
        test_params = [
            ("conf/aaai/2022", False, "https://dblp.org/db/conf/aaai/aaai2022"),
            ("conf/aaai/2022", True, "https://dblp.org/db/conf/aaai/aaai2022.html"),
            ("conf/aaai/aaai2022", False, None),  # entity id is expected not the url id
            (None, False, None),
            ("", False, None),
            (None, True, None),
            ("", True, None),
            ("conf/aaai", False, None),
        ]
        for param in test_params:
            with self.subTest("test dblp url generation", param=param):
                entityId, withPostfix, expected = param
                actual = self.dblpEndpoint.toDblpUrl(entityId, withPostfix)
                self.assertEqual(expected, actual)

    #@unittest.skipIf(Basetest.inPublicCI(), "queries unreliable dblp endpoint")
    def test_getEditorsOfVolume(self):
        """
        tests getEditorsOfVolume
        """
        test_params = [  # (volNumber, {editor:expIds})
            (1, {"Franz": 13, "Manfred": 8, "Martin": 2, "Werner": 10}),
            ("1", {"Franz": 13, "Manfred": 8, "Martin": 2, "Werner": 10}),
            (None, 4600),
        ]
        for param in test_params:
            with self.subTest("test querying of ceurws volume editors", param=param):
                number, expectedEditors = param
                res = self.dblpEndpoint.getEditorsOfVolume(number)
                if number is not None:
                    for editor_record in res:
                        editorName = editor_record.get("name")
                        firstName = editorName.split(" ")[0]
                        self.assertIn(firstName, expectedEditors)
                        self.assertGreaterEqual(
                            len(editor_record), expectedEditors[firstName]
                        )
                else:
                    self.assertGreaterEqual(len(res), expectedEditors)

    #@unittest.skipIf(Basetest.inPublicCI(), "queries unreliable dblp endpoint")
    def test_get_all_ceur_authors(self):
        """
        tests get_all_ceur_authors
        """
        dblp_authors = self.dblpEndpoint.dblp_authors
        dblp_authors.load()
        debug=True
        if debug:
            print(f"found {len(dblp_authors.authors)} authors")
            print(f"found {len(dblp_authors.authorsById)} authors by id")
        self.assertGreaterEqual(len(dblp_authors.authorsById), 75700)
        expected_decker = DblpScholar(
            dblp_author_id="https://dblp.org/pid/d/StefanDecker",
            label="Stefan Decker",
            wikidata_id="Q54303353",
            orcid_id="0000-0001-6324-7164",
            #gnd_id="173443443",
        )
        decker = dblp_authors.authorsById.get("https://dblp.org/pid/d/StefanDecker")
        self.assertEqual(expected_decker, decker)
        
    def test_get_all_ceur_editors(self):
        """
        test get all CEUR-WS editors
        """
        dblp_editors=self.dblpEndpoint.dblp_editors
        dblp_editors.load()
        editors=dblp_editors.editors
        debug=True
        if debug:
            print(f"found {len(editors)} CEUR-WS editors")
        self.assertGreaterEqual(len(editors), 4900)

    #@unittest.skipIf(Basetest.inPublicCI(), "queries unreliable dblp endpoint")
    def test_get_all_ceur_papers(self):
        """
        tests get_all_ceur_papers
        """
        dblp_papers = self.dblpEndpoint.dblp_papers
        dblp_papers.load()
        self.assertGreaterEqual(len(dblp_papers.papers), 40000)
        paper = dblp_papers.papersById.get("https://dblp.org/rec/conf/semweb/FahlHW0D22")
        self.assertIn(
            "https://dblp.org/pid/d/StefanDecker",
            [a.dblp_author_id for a in paper.authors],
        )
        
    def test_dblp_volumes(self):
        """
        test the dblp volumes handling
        """
        dblp_volumes=self.dblpEndpoint.dblp_volumes
        dblp_volumes.load()
        debug=self.debug
        debug=True
        if debug:
            print(f"found {len(dblp_volumes.lod)} volumes")
        # there should be over 2500 dblp indexed volumes so far    
        self.assertGreaterEqual(len(dblp_volumes.lod),2500)

    #@unittest.skipIf(Basetest.inPublicCI(), "queries unreliable dblp endpoint")
    def test_get_ceur_proceeding(self):
        """
        tests retrieving a proceeding from dblp endpoint
        """
        volume = self.dblpEndpoint.get_ceur_proceeding(3262)
        self.assertEqual(
            "https://dblp.org/rec/conf/semweb/2022wikidata", volume.dblp_publication_id
        )
        self.assertEqual(4, len(volume.editors))
        self.assertEqual(16, len(volume.papers))


class TestDblpAuthorIdentifier(Basetest):
    """
    tests DblpAuthorIdentifier
    """

    def test_all(self):
        """
        test if all dblp author identifiers are defined
        """
        ids = DblpAuthorIdentifier.all()
        self.assertGreaterEqual(len(ids), 17)
        for identifier in ids:
            self.assertIsNotNone(identifier.name)
            self.assertIsNotNone(identifier.dblp_property)
