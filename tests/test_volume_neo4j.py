import unittest
from neo4j import GraphDatabase
import json
from ceurws.volume_neo4j import Volume, Editor
from ceurws.location import LocationLookup

# Set up a test Neo4j database connection
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))


class TestVolumeEditorLocation(unittest.TestCase):
    """
    Unit tests for Volume, Editor, and Location classes.
    """

    def test_editor_create_editor_node(self):
        """
        Test the create_editor_node method of the Editor class.
        """
        with driver.session() as session:
            editor = Editor(name="John Doe", likelihood=0.8)
            editor_id = editor.create_editor_node(session.write_transaction)
            self.assertIsNotNone(editor_id)

    def test_volume_create_node(self):
        """
        Test the create_node method of the Volume class.
        """
        with driver.session() as session:
            volume = Volume(acronym="CILC 2023",
                            title="Proceedings of the 38th Italian Conference on Computational Logic",
                            loctime="Udine, Italy, June 21-23, 2023")
            volume_id = volume.create_node(session.write_transaction)
            self.assertIsNotNone(volume_id)

    def test_location_lookup(self):
        """
        Test the lookup method of the LocationLookup class.
        """
        location_lookup = LocationLookup()
        location = location_lookup.lookup("Amsterdam, Netherlands")
        self.assertIsNotNone(location)
        self.assertEqual(location.city, "Amsterdam")
        self.assertEqual(location.country, "Netherlands")

    def test_parse_args(self):
        """
        Test the parse_args function.
        """
        source=Volume.default_source()
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

if __name__ == '__main__':
    unittest.main()
