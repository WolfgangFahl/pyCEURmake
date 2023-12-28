"""
Created on 2023-12-28

@author: wf
"""
from ceurws.urn import URN
from tests.basetest import Basetest


class TestURN(Basetest):
    """
    Test URN checkdigit calculation
    """

    def test_urn_check_digits(self):
        """
        test some examples
        """
        debug = self.debug
        verbose = False
        urns = [
            "urn:nbn:de:0183-mbi0003721",
            "urn:nbn:de:0074-1000-9",
            "urn:nbn:de:0074-1001-3",
            "urn:nbn:de:0074-1002-6",
            "urn:nbn:de:0074-1003-0",
            "urn:nbn:de:0074-1004-3",
            "urn:nbn:de:0074-1005-7",
            "urn:nbn:de:0074-1006-1",
            "urn:nbn:de:0074-1007-4",
            "urn:nbn:de:0074-1008-8",
            "urn:nbn:de:0074-1009-5",
            "urn:nbn:de:0074-1010-3",
            "urn:nbn:de:0074-1011-6",
            "urn:nbn:de:0074-1012-0",
            "urn:nbn:de:0074-1013-3",
            "urn:nbn:de:0074-1014-7",
            "urn:nbn:de:0074-1015-0",
            "urn:nbn:de:0074-1016-4",
            "urn:nbn:de:0074-1017-8",
        ]
        for i, urn in enumerate(urns, start=1):
            urn_prefix = urn[:-1]
            expected = urn[-1]
            digit = URN.calc_urn_checksum(urn_prefix)
            if verbose:
                check_mark = "✅" if expected == str(digit) else "❌"
                print(f"{i:2} {check_mark}:{digit}:{urn_prefix}:{urn}")

        for urn in urns:
            self.assertTrue(URN.check_urn_checksum(urn, debug))
