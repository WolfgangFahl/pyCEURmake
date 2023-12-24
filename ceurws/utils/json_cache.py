import os
from pathlib import Path
from typing import Union

from orjson import orjson
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class CacheInfo:
    name: str
    size: int  # size in bytes
    count: Optional[int] = None  # number of items in the cache, if applicable
    last_accessed: Optional[datetime] = None  # last accessed timestamp

class JsonCacheManager():
    """
    a json based cache manager
    """

    def __init__(self):
        """
        constructor
        """
        self.lods={}
        self.cache_infos={}

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
                self.update_cache_info(lod_name,lod)
        return lod
    
    def update_cache_info(self,lod_name,lod):
        """
        update my cache info
        """
        self.lods[lod_name]=lod
        self.cache_infos[lod_name]=self.get_cache_info(lod_name)
 
    def is_stored(self, json_path: str) -> bool:
        """
        Returns true if given path exists and is not null
        """
        stored= os.path.isfile(json_path) and os.path.getsize(json_path) > 1
        return stored

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
        self.update_cache_info(lod_name,lod)
        
    def get_cache_info(self, lod_name: str) -> CacheInfo:
        """
        Get information about the cache.

        Args:
            lod_name(str): the name of the list of dicts cache to inspect
        Returns:
            CacheInfo: the information about the cache
        """
        json_path = self.json_path(lod_name)
        size = os.path.getsize(json_path) if os.path.isfile(json_path) else 0
        last_accessed = datetime.fromtimestamp(os.path.getmtime(json_path)) if os.path.isfile(json_path) else None
        count=0
        if lod_name in self.lods:
            lod = self.lods[lod_name]
            count = len(lod) if lod else 0
        cache_info = CacheInfo(name=lod_name, size=size, count=count, last_accessed=last_accessed)
        return cache_info