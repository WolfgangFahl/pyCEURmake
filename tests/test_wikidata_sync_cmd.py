"""
Created on 2026-10-25

@author: wf
"""

import io
import os
import unittest
from contextlib import redirect_stdout

from ceurws.ceur_ws_web_cmd import main
from tests.basetest import Basetest


class TestWikidataSyncCmd(Basetest):
    """
    test the command line Wikidata sync of volumes, see
    https://github.com/WolfgangFahl/pyCEURmake/issues/115
    """

    @unittest.skipIf(
        Basetest.inPublicCI() or not os.path.isfile(os.path.expanduser("~/.ceurws/ceurws.db")),
        "needs the local volume cache and the Wikidata endpoint",
    )
    def test_dry_run(self):
        """
        a dry run over a range reports the volumes and their proceedings records
        without writing anything
        """
        out = io.StringIO()
        with redirect_stdout(out):
            exit_code = main(["--wikidata_sync", "4298-4299", "--dry_run"])
        text = out.getvalue()
        self.assertEqual(0, exit_code)
        self.assertIn("Vol-4298", text)
        self.assertIn("Vol-4299", text)
        self.assertIn("dry run", text)
        self.assertIn("2 volumes", text)
