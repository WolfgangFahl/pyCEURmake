# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

pyCEURmake is a Python implementation for parsing, managing, and browsing CEUR Workshop Proceedings (https://ceur-ws.org/). The project scrapes volume metadata from CEUR-WS.org, enriches it with location/time data, integrates with Wikidata and DBLP, and provides both a web interface and CLI tools for browsing proceedings.

## Core Commands

### Testing
```bash
# Run all tests with unittest discover (default)
scripts/test

# Run tests with tox (recommended for comprehensive testing)
scripts/test --tox

# Run tests module by module
scripts/test --module

# Run tests with green (requires green package)
scripts/test --green

# Run specific test file
python -m unittest tests/test_<module>.py
```

### Linting and Formatting
```bash
# Run linter with auto-fix
tox -e lint

# Format code
tox -e format

# Type checking
tox -e type
```

### Running the Web Server
```bash
# Start the web server (default port 9998)
ceur-ws

# Start with debug mode
ceur-ws -d

# Specify custom port
ceur-ws --port 8080
```

### Data Management
```bash
# Update volumes by parsing index.html for new volumes
ceur-ws --update

# Recreate caches (volume table, etc.)
ceur-ws --recreate

# Update Wikidata sync
ceur-ws --wikidata_update

# Update DBLP cache
ceur-ws --dblp_update

# List all volumes
ceur-ws --list
```

### Documentation
```bash
# Generate documentation (requires mkdocs)
scripts/doc
```

## Architecture

### Data Flow
The system follows this data flow:
1. **Scraping**: `IndexHtmlParser` scrapes CEUR-WS.org index to get volume listings
2. **Parsing**: `VolumeParser` parses individual volume pages to extract metadata
3. **Enhancement**: `LoctimeParser` extracts location/time information from text
4. **Storage**: Data is cached in SQLite (via `pylodstorage`) at `~/.ceurws/`
5. **Synchronization**: `WikidataSync` syncs with Wikidata and DBLP endpoints
6. **Presentation**: Web UI (NiceGUI/FastAPI) and CLI provide access to data

### Key Modules

**Main Package: `ceurws/`**

- **`ceur_ws.py`**: Core domain models (`Volume`, `VolumeManager`, `Paper`, `PaperManager`, `Editor`, `Session`) using JSONAble pattern. These are the main in-memory representations.

- **`models/ceur.py`**: SQLModel definitions (`Volume`, `Paper`) for database persistence. These mirror the JSONAble classes but are SQLModel/SQLAlchemy entities for database storage.

- **`ceur_ws_web_cmd.py`**: CLI command handler (`CeurWsCmd`) that extends `WebserverCmd` from ngwidgets. Entry point for the `ceur-ws` command.

- **`webserver.py`**: FastAPI/NiceGUI web server (`CeurWsWebServer`) providing:
  - Web UI routes: `/volumes`, `/volume/{volnumber}`, `/wikidatasync`
  - JSON APIs: `/volumes.json`, `/papers.json`, `/proceedings.json`, `/papers_dblp.json`

- **`wikidatasync.py`**: Synchronizes CEUR-WS data with Wikidata. Manages property mappings, SPARQL queries, and entity creation/updates.

**Parsers:**
- **`indexparser.py`**: Parses CEUR-WS main index page to extract volume list
- **`volumeparser.py`**: Parses individual volume pages for metadata (title, editors, date, etc.)
- **`papertocparser.py`**: Parses paper table of contents
- **`loctime.py`**: Extracts location and time information using NLP (spaCy)
- **`textparser.py`**: Generic text parsing utilities

**External Services (`services/`):**
- **`entity_fishing.py`**: Entity linking service integration
- **`opentapioca.py`**: Wikidata entity tagging service

**Utilities (`utils/`):**
- **`download.py`**: Downloading and caching utilities
- **`webscrape.py`**: Web scraping helpers

**Data Integration:**
- **`dblp.py`**: DBLP integration for bibliographic data
- **`endpoints.py`**: SPARQL endpoint configurations
- **`namedqueries.py`**: Predefined SPARQL queries

**Views:**
- **`volume_view.py`**: Volume list and detail views for web UI
- **`wikidata_view.py`**: Wikidata sync interface
- **`view.py`**: Generic view components

### Data Models

Two parallel model systems exist:
1. **JSONAble models** in `ceur_ws.py`: Used for in-memory objects, API responses, and JSON serialization
2. **SQLModel models** in `models/ceur.py`: Used for database persistence with SQLAlchemy

Common fields across both:
- **Volume**: `number`, `title`, `acronym`, `url`, `pubDate`, `editors`, `city`, `country`, location/time data
- **Paper**: `id`, `title`, `authors`, `vol_number`, `pdf_name`, `pages`

### Configuration

- **`config.py`**: Configuration constants (cache directory, URLs)
- **`pyproject.toml`**: Project metadata, dependencies, tool configuration (ruff, mypy, tox)
- Package uses `pylodstorage` for database/JSON storage
- Cache location: `~/.ceurws/` (configurable via `CEURWS` class)

### Testing

- **`tests/basetest.py`**: Base test class with profiling support, CI detection, and decorators for:
  - `requires_neo4j`: Tests needing local Neo4j instance
  - `requires_sparql_endpoint()`: Tests needing specific SPARQL endpoint
  - `requires_entity_fishing_endpoint`: Entity linking service tests
  - `requires_opentapioca_endpoint`: Entity tagging service tests

Test files follow pattern `test_*.py` and use standard Python unittest framework.

### Dependencies

Key dependencies (see `pyproject.toml`):
- **pybasemkit**: Base module kit for YAML/JSON I/O, logging, CLI tooling
- **ngwidgets**: NiceGUI-based web UI widgets
- **pylodstorage**: Linked Open Data storage (SQLite/SPARQL)
- **geograpy3**: Location extraction and geocoding
- **py-ez-wikidata**: Wikidata integration
- **BeautifulSoup4/lxml**: HTML parsing
- **FastAPI/NiceGUI**: Web framework
- **spaCy**: NLP for location/time extraction
- **neo4j**: Optional Neo4j graph database support
- **SQLModel**: SQL database ORM

## Important Patterns

### Parser Configuration
Most parsers accept a `ParserConfig` object that controls:
- `progress_bar`: tqdm progress bar for user feedback
- `debug`: Enable debug logging

### Manager Pattern
The codebase uses manager classes for collections:
- `VolumeManager`: Manages collection of volumes, handles loading/saving
- `PaperManager`: Manages collection of papers

Managers typically provide:
- `load()`: Load from cache or remote
- `getList()`: Get list of items
- `getById()`: Retrieve by identifier
- `recreate()`: Force rebuild of cache
- `update()`: Incremental update

### Cache Management
- Data is cached in `~/.ceurws/` directory
- `pylodstorage` handles SQLite storage and JSON serialization
- Use `force_query=True` to bypass cache and force fresh data fetch

### External Service Integration
When working with external services (Wikidata, DBLP, entity fishing), always:
- Check availability before running tests (use pytest skip decorators)
- Handle network errors gracefully
- Respect rate limits

## Line Length

The project uses a 120-character line length limit (configured in ruff settings).

## Python Version

Requires Python 3.10+. The project is tested on Python 3.10, 3.11, and 3.12.
