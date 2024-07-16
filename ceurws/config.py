import os
from pathlib import Path

from lodstorage.storageconfig import StorageConfig


class CEURWS:
    """
    CEUR-WS
    """

    @staticmethod
    def get_home_path() -> Path:
        """
        Get home path
        """
        home = Path.home()
        if "GITHUB_WORKSPACE" in os.environ:
            home = Path(os.environ["GITHUB_WORKSPACE"])
        return home

    URL = "http://ceur-ws.org"
    home = get_home_path()
    CACHE_DIR = home.joinpath(".ceurws")
    CACHE_FILE = CACHE_DIR.joinpath("ceurws.db")
    CACHE_HTML = CACHE_DIR.joinpath("index.html")
    CONFIG = StorageConfig(cacheFile=str(CACHE_FILE))
