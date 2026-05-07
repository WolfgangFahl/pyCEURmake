# pyCEURmake

CEUR make python implementation for https://ceur-ws.org/

| | |
| :--- | :--- |
| **PyPi** | [![PyPI Status](https://img.shields.io/pypi/v/pyCEURmake.svg)](https://pypi.python.org/pypi/pyCEURmake/) [![License](https://img.shields.io/github/license/WolfgangFahl/pyCEURmake.svg)](https://www.apache.org/licenses/LICENSE-2.0) [![pypi](https://img.shields.io/pypi/pyversions/pyCEURmake)](https://pypi.org/project/pyCEURmake/) [![format](https://img.shields.io/pypi/format/pyCEURmake)](https://pypi.org/project/pyCEURmake/) [![downloads](https://img.shields.io/pypi/dd/pyCEURmake)](https://pypi.org/project/pyCEURmake/) |
| **GitHub** | [![Github Actions Build](https://github.com/WolfgangFahl/pyCEURmake/actions/workflows/build.yml/badge.svg)](https://github.com/WolfgangFahl/pyCEURmake/actions/workflows/build.yml) [![Release](https://img.shields.io/github/v/release/WolfgangFahl/pyCEURmake)](https://github.com/WolfgangFahl/pyCEURmake/releases) [![Contributors](https://img.shields.io/github/contributors/WolfgangFahl/pyCEURmake)](https://github.com/WolfgangFahl/pyCEURmake/graphs/contributors) [![Last Commit](https://img.shields.io/github/last-commit/WolfgangFahl/pyCEURmake)](https://github.com/WolfgangFahl/pyCEURmake/commits/) [![GitHub issues](https://img.shields.io/github/issues/WolfgangFahl/pyCEURmake.svg)](https://github.com/WolfgangFahl/pyCEURmake/issues) [![GitHub closed issues](https://img.shields.io/github/issues-closed/WolfgangFahl/pyCEURmake.svg)](https://github.com/WolfgangFahl/pyCEURmake/issues/?q=is%3Aissue+is%3Aclosed) |
| **Code** | [![style-black](https://img.shields.io/badge/%20style-black-000000.svg)](https://github.com/psf/black) [![imports-isort](https://img.shields.io/badge/%20imports-isort-%231674b1)](https://pycqa.github.io/isort/) [![Join the discussion at https://github.com/WolfgangFahl/pyCEURmake/discussions](https://img.shields.io/github/discussions/WolfgangFahl/pyCEURmake)](https://github.com/WolfgangFahl/pyCEURmake/discussions) |
| **Docs** | [![API Docs](https://img.shields.io/badge/API-Documentation-blue)](https://WolfgangFahl.github.io/pyCEURmake/) [![formatter-docformatter](https://img.shields.io/badge/%20formatter-docformatter-fedcba.svg)](https://github.com/PyCQA/docformatter) [![style-google](https://img.shields.io/badge/%20style-google-3666d6.svg)](https://google.github.io/styleguide/pyguide.html#s3.8-comments-and-docstrings) |
| **Cite** | [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20034998.svg)](https://doi.org/10.5281/zenodo.20034998) |

## Cite as

If you use pyCEURmake in your research, please cite it via its Zenodo concept DOI
(which always resolves to the latest version):

> Fahl, W., Holzheim, T., & Ayan9801.
> *pyCEURmake — Python implementation for CEUR Workshop Proceedings.*
> Zenodo. https://doi.org/10.5281/zenodo.20034998

Machine-readable metadata is available in [`CITATION.cff`](./CITATION.cff);
GitHub's "Cite this repository" button and Zenodo pick it up automatically.
For a specific release, use the version DOI shown on the corresponding
[Zenodo record](https://doi.org/10.5281/zenodo.20034998).

## Docs and Tutorials
[Wiki](https://wiki.bitplan.com/index.php/PyCEURmake)

## Demos
[CEUR-Volume Browser at RWTH Aachen i5](http://cvb.wikidata.dbis.rwth-aachen.de/)
## Installation
```
pipx install pyCEURmake
```
## Usage
```
usage: ceur-ws [-h] [-a] [-d] [--debugLocalPath DEBUGLOCALPATH]
               [--debugPort DEBUGPORT] [--debugRemotePath DEBUGREMOTEPATH]
               [--debugServer DEBUGSERVER] [-f] [-q] [-v] [-V]
               [--apache APACHE] [-c] [-l] [-i INPUT] [-rol] [--host HOST]
               [--port PORT] [-s] [-dbu] [-nq] [-den DBLP_ENDPOINT_NAME]
               [--list] [-rc] [-uv] [-wen WIKIDATA_ENDPOINT_NAME] [-wdu]

CEUR-WS Volume browser

options:
  -h, --help            show this help message and exit
  -a, --about           show version info and open documentation
  -d, --debug           enable debug output
  --debugLocalPath DEBUGLOCALPATH
                        remote debug Server path mapping - localPath - path on
                        machine where python runs
  --debugPort DEBUGPORT
                        remote debug Port [default: 5678]
  --debugRemotePath DEBUGREMOTEPATH
                        remote debug Server path mapping - remotePath - path
                        on debug server
  --debugServer DEBUGSERVER
                        remote debug Server
  -f, --force           force overwrite or unsafe actions
  -q, --quiet           suppress all output
  -v, --verbose         increase output verbosity
  -V, --version         show program's version number and exit
  --apache APACHE       create an apache configuration file for the given
                        domain
  -c, --client          start client
  -l, --local           run with local file system access
  -i INPUT, --input INPUT
                        input file
  -rol, --render_on_load
                        render on load
  --host HOST           the host to serve / listen from (default: localhost)
  --port PORT           the port to serve from (default: 9998)
  -s, --serve           start webserver
  -dbu, --dblp_update   update dblp cache
  -nq, --namedqueries   generate named queries [default: False]
  -den DBLP_ENDPOINT_NAME, --dblp_endpoint_name DBLP_ENDPOINT_NAME
                        name of dblp endpoint to use dblp-qlever
  --list                list all volumes [default: False]
  -rc, --recreate       recreate caches e.g. volume table
  -uv, --update         update volumes by parsing index.html adding recently
                        published volumes
  -wen WIKIDATA_ENDPOINT_NAME, --wikidata_endpoint_name WIKIDATA_ENDPOINT_NAME
                        name of wikidata endpoint to use wikidata
  -wdu, --wikidata_update
                        update tables from wikidata
```
