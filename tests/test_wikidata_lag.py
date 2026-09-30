"""
Created on 2026-09-30

@author: wf
"""

from argparse import ArgumentParser
from unittest.mock import MagicMock, patch

from ceurws.ceur_ws_web_cmd import CeurWsCmd
from ceurws.wikidata_lag import WikidataLag
from tests.basetest import Basetest


class TestWikidataLag(Basetest):
    """
    test the wait for the replication lag of Wikidata
    see https://github.com/WolfgangFahl/pyCEURmake/issues/111
    """

    def setUp(self, debug=False, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)

    def test_limit(self):
        """
        test that the limit is the maxlag of the Wikidata client
        """
        wikidata_lag = WikidataLag(timeout_minutes=5.0)
        self.assertEqual(5, wikidata_lag.limit)
        self.assertEqual("https://www.wikidata.org/w/api.php", wikidata_lag.api_url)
        self.assertEqual(
            "Wikidata lag stayed above the 5 seconds max lag for edits for 5 minutes.",
            wikidata_lag.timeout_message(),
        )
        self.assertEqual(
            "Vol 4237 (2 of 3): Wikidata lag is 9.3 seconds, more than the 5 seconds max lag for edits. "
            "Waiting, minute 3 of 5 …",
            wikidata_lag.wait_message("Vol 4237 (2 of 3)", 9.316666666666666, 130.0),
        )

    def test_get_lag(self):
        """
        test reading the lag from the API answer
        """
        wikidata_lag = WikidataLag(timeout_minutes=5.0)
        lagged = {"error": {"code": "maxlag", "lag": 9.316666666666666, "type": "wikibase-queryservice"}}
        for answer, expected in [(lagged, 9.316666666666666), ({"batchcomplete": ""}, 0.0)]:
            response = MagicMock()
            response.json.return_value = answer
            with patch("ceurws.wikidata_lag.requests.get", return_value=response) as get:
                lag = wikidata_lag.get_lag()
            self.assertEqual(expected, lag)
            self.assertEqual(-1, get.call_args.kwargs["params"]["maxlag"])

    def test_ready_at_once(self):
        """
        test that there is no wait without lag
        """
        wikidata_lag = WikidataLag(timeout_minutes=5.0)
        on_wait = MagicMock()
        with patch.object(WikidataLag, "get_lag", return_value=0.4), patch("ceurws.wikidata_lag.time.sleep") as sleep:
            ready = wikidata_lag.wait_until_ready(on_wait)
        self.assertTrue(ready)
        sleep.assert_not_called()
        on_wait.assert_not_called()

    def test_wait_until_lag_drops(self):
        """
        test waiting while the lag is above the limit
        """
        wikidata_lag = WikidataLag(timeout_minutes=5.0, poll_seconds=10.0)
        on_wait = MagicMock()
        with (
            patch.object(WikidataLag, "get_lag", side_effect=[9.3, 6.0, 5.0]),
            patch("ceurws.wikidata_lag.time.sleep") as sleep,
        ):
            ready = wikidata_lag.wait_until_ready(on_wait)
        self.assertTrue(ready)
        self.assertEqual(2, sleep.call_count)
        self.assertEqual([9.3, 6.0], [call.args[0] for call in on_wait.call_args_list])

    def test_timeout(self):
        """
        test giving up when the lag stays above the limit for the timeout
        """
        wikidata_lag = WikidataLag(timeout_minutes=5.0, poll_seconds=10.0)
        clock = {"now": 1000.0}

        def sleep(seconds: float) -> None:
            clock["now"] += seconds

        with (
            patch.object(WikidataLag, "get_lag", return_value=9.3) as get_lag,
            patch("ceurws.wikidata_lag.time.sleep", side_effect=sleep),
            patch("ceurws.wikidata_lag.time.monotonic", side_effect=lambda: clock["now"]),
        ):
            ready = wikidata_lag.wait_until_ready()
        self.assertFalse(ready)
        self.assertEqual(300.0, clock["now"] - 1000.0)
        self.assertEqual(31, get_lag.call_count)

    def test_command_line_option(self):
        """
        test the --wikidata_timeout option and its default of 5 minutes
        """
        cmd = CeurWsCmd.__new__(CeurWsCmd)
        with patch("ceurws.ceur_ws_web_cmd.WebserverCmd.getArgParser", return_value=ArgumentParser()):
            parser = cmd.getArgParser("test", "test version")
        self.assertEqual(5.0, parser.parse_args([]).wikidata_timeout)
        self.assertEqual(2.5, parser.parse_args(["--wikidata_timeout", "2.5"]).wikidata_timeout)
        self.assertEqual(10.0, parser.parse_args(["-wto", "10"]).wikidata_timeout)
