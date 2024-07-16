import json
import logging
import os
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_index_pages():
    try:
        url = "https://github.com/WolfgangFahl/pyCEURmake/releases/download/v0.4.0/volume_index_pages.zip"
        logger.info(f"Downloading ceur-ws volume index pages from {url}...")
        with urlopen(url) as resp:
            zip_file = ZipFile(BytesIO(resp.read()))
        target_location = cache_path()
        logger.info(f"Extracting ceur-ws volume index pages and storing them at {target_location}...")
        target_location.mkdir(parents=True, exist_ok=True)
        zip_file.extractall(target_location)
    except Exception as e:
        logger.exception(e)


def download_volumes_json():
    try:
        url = "http://cvb.bitplan.com/volumes.json"
        logger.info(f"Downloading ceur-ws volumes json from {url}...")
        with urlopen(url) as resp:
            data = json.load(resp)
        target_location = cache_path() / "volumes.json"
        logger.info(f"Extracting ceur-ws volumes json to {target_location}...")
        target_location.parent.mkdir(parents=True, exist_ok=True)
        with open(target_location, mode="w", encoding="utf-8") as fp:
            json.dump(data, fp)
    except Exception as e:
        logger.error(e)


def download_db():
    db_file = cache_path() / "ceurws.db"
    if db_file.is_file() and db_file.exists():
        logger.info("ceurws.db already exists")
    else:
        url = "https://github.com/WolfgangFahl/pyCEURmake/releases/download/v0.4.0/ceurws.db.zip"
        logger.info(f"ceurws.db missing → start download from {url}")
        try:
            with urlopen(url) as resp:
                zip_file = ZipFile(BytesIO(resp.read()))
            target_location = cache_path()
            logger.info("Storing ceurws.db at {target_location}")
            target_location.mkdir(parents=True, exist_ok=True)
            zip_file.extractall(target_location)
        except Exception as e:
            logger.error(e)


def get_home_path() -> Path:
    """
    Get home path
    """
    home = Path.home()
    if "GITHUB_WORKSPACE" in os.environ:
        home = Path(os.environ["GITHUB_WORKSPACE"])
    return home


def cache_path() -> Path:
    home = get_home_path()
    return home / ".ceurws"


download_index_pages()
download_volumes_json()
download_db()
