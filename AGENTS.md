# AGENTS.md - Guidance for Agentic Coding Tools

This file provides guidance for agentic coding agents working in the pyCEURmake repository.

## Build/Lint/Test Commands

### Running Tests

**IMPORTANT**: `scripts/test` runs the full suite (~2.5 minutes). Do NOT run it to verify a small fix.

For targeted verification after a fix, run only the relevant test file or method:

```bash
# Run a single test method (preferred for quick verification)
python -m unittest tests.test_ceur.TestCEUR.testCEUR

# Run a specific test file
python -m unittest tests/test_<module>.py

# Run all tests (full suite, ~2.5 minutes - only when explicitly requested)
scripts/test

# Run tests with tox (comprehensive - only when explicitly requested)
scripts/test --tox

# Run tests module by module
scripts/test --module
```

### Linting and Formatting

```bash
# Run linter with auto-fix
tox -e lint

# Format code
tox -e format

# Type checking
tox -e type

# Run ruff directly
ruff check --fix
ruff format
```

### Running the Application

```bash
# Start web server (default port 9998)
ceur-ws -d --port 8080
```

## Code Style Guidelines

### General Rules
- **Line length**: 120 characters (configured in ruff)
- **Python version**: 3.10+ (tested on 3.10, 3.11, 3.12)
- **Docstrings**: Use triple quotes; include description, args, return types
- **Comments**: Avoid adding comments unless explicitly requested

### Imports
- Standard library imports first, then third-party, then local
- Use absolute imports (e.g., `from ceurws.config import CEURWS`)
- Group imports with blank lines between groups
- Sort imports with ruff (isort rules enabled)

```python
import datetime
import re
from typing import Optional

import dateutil.parser
from bs4 import BeautifulSoup
from geograpy.locator import City, Country

from ceurws.config import CEURWS
from ceurws.indexparser import IndexHtmlParser
```

### Type Hints
- Use modern Python type hints (Python 3.10+): `int | None` instead of `Optional[int]`
- Use `from __future__ import annotations` when forward references are needed
- Be explicit with return types

```python
def __init__(
    self,
    number: int | None = None,
    title: str | None = None,
    editors: list["Editor"] | None = None,
) -> None:
    ...
```

### Naming Conventions
- **Classes**: `PascalCase` (e.g., `VolumeManager`, `PaperTocParser`)
- **Functions/methods**: `snake_case` (e.g., `get_samples()`, `parse_volume()`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `CEURWS_BASE_URL`)
- **Private methods**: Leading underscore (e.g., `_parse_html()`)
- **File names**: `snake_case.py` (e.g., `volumeparser.py`)

### Error Handling
- Use specific exception types rather than bare `except`
- Handle network errors gracefully when calling external services
- Use pytest skip decorators for tests requiring external services

```python
try:
    result = fetch_data(url)
except requests.RequestException as e:
    logger.warning(f"Failed to fetch {url}: {e}")
    return None

@requires_sparql_endpoint("https://query.wikidata.org/sparql")
def test_wikidata_query(self):
    ...
```

### Code Patterns

**Manager Pattern**: Manager classes for collections (`VolumeManager`, `PaperManager`) with methods: `load()`, `getList()`, `getById()`, `recreate()`, `update()`

**Parser Configuration**: Most parsers accept a `ParserConfig` object with `progress_bar` and `debug` flags.

**Data Models**: Two parallel systems - JSONAble in `ceur_ws.py` and SQLModel in `models/ceur.py`

**Test Base Class**: Use `Basetest` from `tests.basetest` with debug/profile flags and decorators like `@requires_neo4j`, `@requires_sparql_endpoint()`

```python
from tests.basetest import Basetest

class TestVolume(Basetest):
    def setUp(self, debug=True, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
```

### Configuration
- Configuration constants in `ceurws/config.py`
- Cache location: `~/.ceurws/` (configurable via `CEURWS` class)
- Use `force_query=True` to bypass cache

### External Services
When working with external services (Wikidata, DBLP, entity fishing):
- Check availability before running tests (use pytest skip decorators)
- Handle network errors gracefully
- Use caching to minimize API calls

### Ruff Configuration
- Rules: `E` (pycodestyle), `F` (Pyflakes), `UP` (pyupgrade), `B` (flake8-bugbear), `SIM` (flake8-simplify), `I` (isort)
- Ignored: `SIM108` (if-else-block-instead-of-if-exp)

### Testing Best Practices
- Use unittest framework; name test methods starting with `test_`
- Use assertions with descriptive messages
- Use the `debug` flag in tests for verbose output

### File Organization
```
ceurws/
    __init__.py          # Package init, version
    ceur_ws.py           # Core models (Volume, Paper, Editor, Session)
    ceur_ws_web_cmd.py   # CLI command handler
    webserver.py         # FastAPI/NiceGUI web server
    wikidatasync.py      # Wikidata synchronization
    config.py            # Configuration constants
    indexparser.py       # CEUR-WS index parser
    volumeparser.py      # Volume page parser
    papertocparser.py    # Paper table of contents parser
    loctime.py           # Location/time extraction
    models/ceur.py       # SQLModel definitions
    services/            # External services
    utils/               # Utility functions
    views/               # Web UI views

tests/
    basetest.py          # Base test class
    test_*.py            # Test files
```

## Project Overview
pyCEURmake is a Python implementation for parsing, managing, and browsing CEUR Workshop Proceedings (https://ceur-ws.org/). It scrapes volume metadata from CEUR-WS.org, enriches it with location/time data, integrates with Wikidata and DBLP, and provides a web interface and CLI tools.
