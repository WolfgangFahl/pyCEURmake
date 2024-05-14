import json
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile


def download_index_pages():
    print("Downloading ceur-ws volume index pages... ", end="", flush=True)
    try:
        url = "https://github.com/WolfgangFahl/pyCEURmake/releases/download/v0.4.0/volume_index_pages.zip"
        with urlopen(url) as resp:
            zip_file = ZipFile(BytesIO(resp.read()))
        target_location = Path.home().joinpath(".ceurws")
        target_location.mkdir(parents=True, exist_ok=True)
        zip_file.extractall(target_location)
        print("✅")
    except Exception as e:
        print("❌")
        print(e)


def download_volumes_json():
    print("Downloading ceur-ws volumes json... ", end="", flush=True)
    try:
        url = "http://cvb.bitplan.com/volumes.json"
        with urlopen(url) as resp:
            data = json.load(resp)
        target_location = Path.home().joinpath(".ceurws", "volumes.json")
        target_location.parent.mkdir(parents=True, exist_ok=True)
        with open(target_location, mode="w", encoding="utf-8") as fp:
            json.dump(data, fp)
        print("✅")
    except Exception as e:
        print("❌")
        print(e)


def download_db():
    db_file = Path.home().joinpath(".ceurws", "ceurws.db")
    if db_file.is_file() and db_file.exists():
        print("ceurws.db already exists")
    else:
        print("ceurws.db missing → start download", end="", flush=True)
        url = "https://github.com/WolfgangFahl/pyCEURmake/releases/download/v0.4.0/ceurws.db.zip"
        try:
            with urlopen(url) as resp:
                zip_file = ZipFile(BytesIO(resp.read()))
            target_location = Path.home().joinpath(".ceurws")
            target_location.mkdir(parents=True, exist_ok=True)
            zip_file.extractall(target_location)
            print("✅")
        except Exception as e:
            print("❌")
            print(e)


download_index_pages()
download_volumes_json()
download_db()
