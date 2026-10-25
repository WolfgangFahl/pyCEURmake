"""
Created on 2026-10-25

@author: wf
"""

from ceurws.volume_range import VolumeRange
from tests.basetest import Basetest


class TestVolumeRange(Basetest):
    """
    test the volume range parsing of the command line, see
    https://github.com/WolfgangFahl/pyCEURmake/issues/115
    """

    def test_numbers(self):
        """
        ranges and single numbers give a sorted list without duplicates
        """
        cases = [
            (["4065-4069"], [4065, 4066, 4067, 4068, 4069]),
            (["4003", "4065-4067", "4003"], [4003, 4065, 4066, 4067]),
            (["Vol-4298", "vol-4299"], [4298, 4299]),
            ([], []),
        ]
        for args, expected in cases:
            self.assertEqual(expected, VolumeRange.numbers(args), args)

    def test_invalid(self):
        """
        a range that is no range raises a ValueError naming the text
        """
        for text in ["abc", "4069-4065", "4065-"]:
            with self.assertRaises(ValueError) as context:
                VolumeRange.numbers([text])
            self.assertIn(text, str(context.exception))
