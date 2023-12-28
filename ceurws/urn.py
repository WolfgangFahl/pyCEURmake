"""
Created on 2023-12-28

@author: wf / ChatGPT-4 as instructed
"""


class URN:
    """
    URN check digit calculator for DNB URN service:

    see https://www.dnb.de/DE/Professionell/Services/URN-Service/urn-service_node.html

    and
        https://d-nb.info/1045320641/34
        http://nbn-resolving.de/nbnpruefziffer.php

    """

    @classmethod
    def check_urn_checksum(cls, urn: str, debug: bool = False) -> bool:
        urn_check_digit_str=urn[-1]
        urn_prefix = urn[:-1]
        check_digit = cls.calc_urn_checksum(urn_prefix, debug)
        urn_ok = str(check_digit) == urn_check_digit_str
        return urn_ok

    @classmethod
    def calc_urn_checksum(cls, test_urn: str, debug: bool = False) -> int:
        """
        converted from PHP and JavaScript code see
        see https://github.com/bohnelang/URN-Pruefziffer

        Args:
            debug(bool) if True show the internal values while calculating
        """
        # Code string provided in the original PHP function
        code = "3947450102030405060708094117############1814191516212223242542262713282931123233113435363738########43"

        # Initialization of variables
        _sum = 0
        pos = 1

        # Iterating through each character in the URN
        for i, char in enumerate(test_urn.upper()):
            # Getting the ASCII value and adjusting it based on the character '-' (45 in ASCII)
            x = ord(char) - 45
            # Extracting two consecutive values from the code string
            v1 = int(code[x * 2]) if code[x * 2] != "#" else 0
            v2 = int(code[x * 2 + 1]) if code[x * 2 + 1] != "#" else 0

            if v1 == 0:
                # If v1 is 0, increment pos after multiplying v2 with its current value
                _sum += v2 * pos
                pos += 1  # post-increment equivalent in Python
            else:
                # If v1 is not 0, use pos for the first term, increment pos, then use the new value of pos for the second term
                # This effectively increases pos by 2 in this branch
                _sum += pos * v1
                pos += 1  # increment for the first term
                _sum += v2 * pos  # use incremented pos for the second term
                pos += 1  # increment for the second term

            if debug:
                print(
                    f"i: {i:2} pos: {pos:2} x: {x:2} v1: {v1:2} v2: {v2:2} sum: {_sum:4}"
                )

        # Assuming v2 is not 0 at the end of your URN calculations
        check_digit = (_sum // v2) % 10  # Using integer division for floor behavior

        return check_digit
