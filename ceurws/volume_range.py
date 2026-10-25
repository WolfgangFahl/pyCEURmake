"""
Created on 2026-10-25

@author: wf
"""

import re


class VolumeRange:
    """
    volume numbers and ranges as given on the command line, e.g. 4065-4069 4003 Vol-4298,
    see https://github.com/WolfgangFahl/pyCEURmake/issues/115
    """

    pattern = re.compile(r"^(?:vol-)?(\d+)(?:-(\d+))?$", re.IGNORECASE)

    @classmethod
    def numbers(cls, texts: list[str]) -> list[int]:
        """
        get the sorted volume numbers of the given texts without duplicates

        Args:
            texts: the texts, each a number, a range of two numbers joined by a dash
                or a number with a Vol- prefix

        Returns:
            list[int]: the sorted volume numbers

        Raises:
            ValueError: if a text is no number or range or the range runs backwards
        """
        numbers = set()
        for text in texts:
            match = cls.pattern.match(text.strip())
            if match is None:
                raise ValueError(f"invalid volume range {text}")
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else start
            if end < start:
                raise ValueError(f"invalid volume range {text}: {end} is below {start}")
            numbers.update(range(start, end + 1))
        result = sorted(numbers)
        return result
