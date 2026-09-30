"""
Created on 2026-09-30

@author: wf
"""

import inspect
import time
from collections.abc import Callable

import requests
from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator.wbi_helpers import mediawiki_api_call_helper

from ceurws.config import CEURWS


class WikidataLag:
    """
    replication lag of Wikidata

    Wikidata refuses bot writes while its replication lag is above the maxlag of the write.
    The Wikidata client then waits and retries on its own without telling its caller -
    see https://github.com/WolfgangFahl/pyCEURmake/issues/111.
    Waiting here before a write keeps the wait visible and limits it.
    """

    def __init__(self, timeout_minutes: float, poll_seconds: float = 10.0):
        """
        constructor

        Args:
            timeout_minutes: the minutes to wait for the lag to drop below the limit
            poll_seconds: the seconds between two lag checks
        """
        self.timeout_minutes = timeout_minutes
        self.poll_seconds = poll_seconds
        self.ready = False
        self.api_url = wbi_config["MEDIAWIKI_API_URL"]
        # the maxlag the Wikidata client sends with its writes
        self.limit = inspect.signature(mediawiki_api_call_helper).parameters["maxlag"].default

    def get_lag(self) -> float:
        """
        get the current replication lag

        Returns:
            float: the lag in seconds, 0.0 if the API reports none
        """
        params = {"action": "query", "meta": "siteinfo", "format": "json", "maxlag": -1}
        headers = {"User-Agent": CEURWS.USER_AGENT}
        response = requests.get(self.api_url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        error = response.json().get("error", {})
        lag = float(error.get("lag", 0.0))
        return lag

    def wait_until_ready(self, on_wait: Callable[[float, float], None] | None = None) -> bool:
        """
        wait until the lag allows a write or my timeout is over

        Args:
            on_wait: called with the lag and the elapsed seconds before each wait

        Returns:
            bool: True if Wikidata accepts writes, False if the lag stayed above the limit until the timeout
        """
        start = time.monotonic()
        ready = False
        waiting = True
        while waiting:
            lag = self.get_lag()
            elapsed = time.monotonic() - start
            if lag <= self.limit:
                ready = True
                waiting = False
            elif elapsed >= self.timeout_minutes * 60:
                waiting = False
            else:
                if on_wait is not None:
                    on_wait(lag, elapsed)
                time.sleep(self.poll_seconds)
        return ready

    def timeout_message(self) -> str:
        """
        get the message for a lag that did not drop in time

        Returns:
            str: the message
        """
        message = f"Wikidata lag stayed above {self.limit} s for {self.timeout_minutes:g} min"
        return message
