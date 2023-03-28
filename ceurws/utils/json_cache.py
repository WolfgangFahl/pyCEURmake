import os
from pathlib import Path
from typing import Union

from orjson import orjson


class JsonCacheManager():
    """
    a json based cache manager
    """

    def __init__(self):
        """
        constructor
        """

    def json_path(self, lod_name: str) -> str:
        """
        get the json path for the given list of dicts name

        Args:
            lod_name(str): the name of the list of dicts cache to read

        Returns:
            str: the path to the list of dict cache
        """
        root_path = f"{Path.home()}/.ceurws"
        json_path = f"{root_path}/{lod_name}.json"
        Path(json_path).parent.mkdir(parents=True, exist_ok=True)
        return json_path

    def load(self, lod_name: str) -> Union[list, dict]:
        """
        load my list of dicts

        Args:
            lod_name(str): the name of the list of dicts cache to read

        Returns:
            list: the list of dicts
            None: if lod is not cached
        """
        json_path = self.json_path(lod_name)
        lod = None
        if self.is_stored(json_path):
            with open(json_path) as json_file:
                lod = orjson.loads(json_file.read())
        return lod

    def is_stored(self, json_path: str) -> bool:
        """
        Returns true if given path exists and is not null
        """
        return os.path.isfile(json_path) and os.path.getsize(json_path) > 1


    def store(self, lod_name: str, lod: Union[list, dict]):
        """
        store my list of dicts

        Args:
            lod_name(str): the name of the list of dicts cache to write
            lod(list): the list of dicts to write
        """
        json_path = self.json_path(lod_name)
        json_str = orjson.dumps(lod, option=orjson.OPT_INDENT_2)
        with open(json_path, 'wb') as json_file:
            json_file.write(json_str)
            pass