from io import BytesIO
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

resp = urlopen("https://github.com/WolfgangFahl/pyCEURmake/releases/download/v0.4.0/volume_index_pages.zip")
zip_file = ZipFile(BytesIO(resp.read()))
target_location = Path.home().joinpath(".ceurws")
target_location.mkdir(parents=True, exist_ok=True)
zip_file.extractall(target_location)
