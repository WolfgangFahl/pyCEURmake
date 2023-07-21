import argparse
import os
import sys
import re
import json
from typing import List
from dataclasses import dataclass, field
import requests
from neo4j import GraphDatabase
from typing import Optional

@dataclass
class Volume:
    """
    Represents a volume with its attributes.
    """

    acronym: str
    title: str
    loctime: str
    editors: List['Editor'] = field(default_factory=list)

    @classmethod
    def from_json(cls, json_data):
        """
        Create a Volume instance from JSON data.

        Args:
            json_data (dict): The JSON data representing the volume.

        Returns:
            Volume: The Volume instance created from the JSON data.
        """
        editor_names = json_data.get('editors')
        if editor_names:
            editor_names = editor_names.split(",")
        else:
            editor_names = []
        editors = [Editor(name=name.strip()) for name in editor_names]
        return cls(
            acronym=json_data.get('acronym'),
            title=json_data.get('title'),
            loctime=json_data.get('loctime'),
            editors=editors
        )

    def create_node(self, tx) -> int:
        """
        Create a Volume node in Neo4j.

        Args:
            tx: The Neo4j transaction.

        Returns:
            int: The ID of the created node.
        """
        query = "CREATE (v:Volume {acronym: $acronym, title: $title, loctime: $loctime})"
        parameters = {
            "acronym": self.acronym,
            "title": self.title,
            "loctime": self.loctime
        }
        result = tx.run(query, parameters)
        record = result.single()
        if record is not None:
            return record.value()
        else:
            return None

    @staticmethod
    def load_json_file(source: str) -> List['Volume']:
        """
        Load volumes from the source JSON file.

        Args:
            source (str): Path to the source JSON file.

        Returns:
            List[Volume]: The list of loaded volumes.
        """
        with open(source, 'r') as file:
            json_data = json.load(file)

        volumes = [Volume.from_json(volume_data) for volume_data in json_data]
        return volumes
    
    @classmethod
    def default_source(cls)->str:
        """
        get the default source
        """
        default_source = os.path.expanduser('~/.ceurws/volumes.json')
        return default_source
    
    @classmethod
    def parse_args(cls,argv:list=None):
        """
        Parse command line arguments.
        
        Args:
            argv(list): command line arguments

        Returns:
            argparse.Namespace: The parsed command line arguments.
        """
        
        default_source = cls.default_source()
        parser = argparse.ArgumentParser(description="Volume/Editor/Location Information")
        parser.add_argument('--source', default=default_source, help="Source JSON file path")
        # Add progress option
        parser.add_argument('--progress', action='store_true', help="Display progress information")
  
        return parser.parse_args(argv)

    @staticmethod
    def main(argv=None):
        if argv is None:
            argv=sys.argv[1:]
        args = Volume.parse_args(argv)
        volumes = Volume.load_json_file(args.source)

        # Connect to Neo4j
        driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
        with driver.session() as session:
            for volume in volumes:
                volume_node_id = volume.create_node(session)
                for editor in volume.editors:
                    editor.search_by_name()
                    editor.create_node(session, volume_node_id)


@dataclass
class Editor:
    """
    Represents an editor with their name and ORCID.
    """

    name: str
    orcid: str = None
    likelihood: float = None

    @classmethod
    def from_json(cls, json_data):
        """
        Create an Editor instance from JSON data.

        Args:
            json_data (dict): The JSON data representing the editor.

        Returns:
            Editor: The Editor instance created from the JSON data.
        """
        return cls(
            name=json_data.get('name'),
            orcid=json_data.get('orcid')
        )

    def search_by_name(self):
        """
        Search the editor by name using the ORCID API and calculate the likelihood.
        """
        if self.name:
            url = f"https://pub.orcid.org/v3.0/search/?q={self.name}"
            headers = {
                "Accept": "application/json"
            }
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                num_results = data.get("num-found", 0)
                self.likelihood = num_results / 10  # Arbitrary calculation, adjust as needed

    def create_node(self, tx, volume_node_id: int):
        """
        Create an Editor node in Neo4j.

        Args:
            tx: The Neo4j transaction.
            volume_node_id (int): The ID of the volume node.
        """
        query = """
        MATCH (v:Volume)
        WHERE id(v) = $volume_node_id
        CREATE (v)-[:HAS_EDITOR]->(e:Editor {name: $name, orcid: $orcid, likelihood: $likelihood})
        """
        parameters = {
            "volume_node_id": volume_node_id,
            "name": self.name,
            "orcid": self.orcid,
            "likelihood": self.likelihood
        }
        tx.run(query, parameters)

@dataclass
class Location:
    city: str
    country: str
    date: str

    @staticmethod
    def parse(location_str: str) -> Optional['Location']:
        """
        Parse a location string of the format "City, Country, Date"

        Args:
            location_str: The location string to parse.

        Returns:
            A Location object or None if the string could not be parsed.
        """
        match = re.match(r'^(.*), (.*), (.*)$', location_str)
        if match:
            city, country, date = match.groups()
            return Location(city, country, date)
        else:
            return None

if __name__ == "__main__":
    Volume.main()
