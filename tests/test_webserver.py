"""
Created on 2026-10-23

@author: wf
"""

import inspect
import time

from ngwidgets.webserver_test import WebserverTest

from ceurws.ceur_ws_web_cmd import CeurWsCmd
from ceurws.webserver import CeurWsSolution, CeurWsWebServer


class CeurWsTestCmd(CeurWsCmd):
    """
    command of the test: takes the config and server class that
    WebserverTest passes and ignores them, CeurWsCmd builds its own
    """

    def __init__(self, config, server_class):
        CeurWsCmd.__init__(self)


class TestWebserver(WebserverTest):
    """
    test the CEUR-WS volume browser web server, see
    https://github.com/WolfgangFahl/pyCEURmake/issues/113
    """

    def setUp(self, debug: bool = False, profile: bool = True) -> None:
        WebserverTest.setUp(self, CeurWsWebServer, CeurWsTestCmd, debug=debug, profile=profile)

    def test_volume_route(self) -> None:
        """
        the path placeholder of the volume route and the parameter of its
        handler carry the same name, so that FastAPI reads the volume number
        from the path instead of demanding a query parameter
        """
        path = "/volume/{volnumber}"
        routes = [route for route in self.ws.app.routes if getattr(route, "path", None) == path]
        self.assertEqual(1, len(routes), path)
        parameters = inspect.signature(routes[0].endpoint).parameters
        self.assertIn("volnumber", parameters)
        self.assertTrue(hasattr(CeurWsSolution, "volumePage"))

    def test_volume_page(self) -> None:
        """
        the page of a volume the server holds answers 200 and names the volume
        """
        for _ in range(20):
            if hasattr(self.ws, "wdSync"):
                break
            time.sleep(0.5)
        numbers = sorted(self.ws.wdSync.volumesByNumber.keys()) if hasattr(self.ws, "wdSync") else []
        if not numbers:
            self.skipTest("no volumes loaded")
        number = numbers[-1]
        html = self.get_html(f"/volume/{number}")
        self.assertIn(f"Vol-{number}", html)
