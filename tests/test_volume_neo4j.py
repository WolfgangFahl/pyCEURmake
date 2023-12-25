import json
import os
import unittest

from ceurws.location import LocationLookup
from ceurws.volume_neo4j import Editor, Neo4j, Volume
from tests.basetest import Basetest


class TestVolumeEditorLocation(Basetest):
    """
    Unit tests for Volume, Editor, and Location classes.
    """

    def setUp(self, debug=False, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.neo4j = Neo4j()

    def tearDown(self):
        Basetest.tearDown(self)
        self.neo4j.close()

    def test_neo4j_available(self):
        """
        test the port availability
        """
        for service, port in [("bolt", self.neo4j.bolt_port), ("http", 7474)]:
            available = Neo4j.is_port_available(self.neo4j.host, port)
            self.assertTrue(available, f"{service} service at {port}")

    def create_test_volume(self, year: int = 2023) -> int:
        """
        Creates a test Volume node for the given year.

        Args:
            year (int): The year for which to create the Volume.

        Returns:
            int: The ID of the created Volume node.
        """
        with self.neo4j.driver.session() as session:
            with session.begin_transaction() as tx:
                acronym = f"CILC {year}"
                title = f"Proceedings of the {year-1985}th Italian Conference on Computational Logic"
                loctime = f"Some City, Italy, June 21-23, {year}"
                volume = Volume(acronym=acronym, title=title, loctime=loctime)
                volume_id = volume.create_node(tx)
            return volume_id

    @unittest.skipIf(os.getenv("JENKINS_URL"), "Skipping this test in Jenkins")
    def test_volume_create_node(self):
        """
        Test the create_node method of the Volume class.
        """
        volume_id = self.create_test_volume()
        self.assertIsNotNone(volume_id)

    @unittest.skipIf(os.getenv("JENKINS_URL"), "Skipping this test in Jenkins")
    def test_editor_create_editor_node(self):
        """
        Test the create_editor_node method of the Editor class.
        """
        volume_id_2023 = self.create_test_volume(2023)
        volume_id_2024 = self.create_test_volume(2024)

        with self.neo4j.driver.session() as session:
            with session.begin_transaction() as tx:
                # Test creating one editor for multiple volumes
                editor = Editor(name="John Doe", likelihood=0.8)
                editor_id_2023 = editor.create_node(tx, volume_id_2023)
                editor_id_2024 = editor.create_node(tx, volume_id_2024)

                self.assertIsNotNone(editor_id_2023)
                self.assertIsNotNone(editor_id_2024)

    def test_location_lookup(self):
        """
        Test the lookup method of the LocationLookup class.
        """
        location_lookup = LocationLookup()
        location = location_lookup.lookup("Amsterdam, Netherlands")
        self.assertIsNotNone(location)
        self.assertEqual(location.name, "Amsterdam")
        self.assertEqual(location.country.iso, "NL")

    def test_parse_args(self):
        """
        Test the parse_args function.
        """
        source = Volume.default_source()
        args = Volume.parse_args(["--source", source])
        self.assertEqual(args.source, source)

    def test_json_loading(self):
        """
        Test the JSON loading from a file.
        """
        with open(Volume.default_source()) as file:
            json_data = json.load(file)
        self.assertIsNotNone(json_data)
        pass
