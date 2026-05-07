import os
from pathlib import Path

from lodstorage.sparql import SPARQL
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

    URL = "https://ceur-ws.org"
    home = get_home_path()
    CACHE_DIR = home.joinpath(".ceurws")
    CACHE_FILE = CACHE_DIR.joinpath("ceurws.db")
    CACHE_HTML = CACHE_DIR.joinpath("index.html")
    CONFIG = StorageConfig(cacheFile=str(CACHE_FILE))

    # Default User-Agent used for all SPARQL and HTTP calls made by this
    # project. Wikimedia enforces a descriptive UA policy and rejects
    # default urllib UAs with 403.
    USER_AGENT = (
        "pyCEURmake/1.0 (https://github.com/WolfgangFahl/pyCEURmake)"
    )
    # Conservative per-minute cap for unauthenticated SPARQL / MediaWiki
    # access (Wikidata Query Service).
    SPARQL_CALLS_PER_MINUTE = 60


def make_sparql(
    endpoint_url: str,
    method: str = "POST",
    agent: str | None = None,
    calls_per_minute: int | None = None,
) -> SPARQL:
    """Build a :class:`lodstorage.sparql.SPARQL` client with a proper UA
    and rate-limit, avoiding the 403 response that Wikimedia returns for
    the default urllib User-Agent.

    Args:
        endpoint_url: SPARQL endpoint URL.
        method: HTTP method, default ``POST``.
        agent: optional UA override; defaults to :data:`CEURWS.USER_AGENT`.
        calls_per_minute: optional rate-limit override; defaults to
            :data:`CEURWS.SPARQL_CALLS_PER_MINUTE`.

    Returns:
        Configured :class:`SPARQL` instance.
    """
    used_agent = agent if agent is not None else CEURWS.USER_AGENT
    used_rate = (
        calls_per_minute if calls_per_minute is not None
        else CEURWS.SPARQL_CALLS_PER_MINUTE
    )
    sparql = SPARQL(
        endpoint_url,
        method=method,
        agent=used_agent,
        calls_per_minute=used_rate,
    )
    return sparql
