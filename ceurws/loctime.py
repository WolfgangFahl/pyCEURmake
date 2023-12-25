"""
Created on 2023-12-22

@author: wf
"""
import os
import re
from collections import Counter

import yaml
from tabulate import tabulate


class LoctimeParser:
    """
    A parser class for handling loctime lookups. This class provides methods to
    load, parse, and update loctime data using a dictionary of dictionaries structure.

    Attributes:
        filepath (str): The file path to the loctime YAML configuration.
        lookups (dict): The loaded lookup dictionaries from the YAML file.
        multi_word (dict): A dictionary to handle multi-word keys.
        multi_word_lookups (dict): A version of lookups with keys as concatenated words.
        counters (dict): A dictionary of Counter objects for various categories.
        year_pattern (re.Pattern): A compiled regex pattern to match 4-digit years.
        total_loctimes (int): The total count of processed loctimes.
    """

    def __init__(self, filepath: str = None):
        """
        Initializes the LoctimeParser object, setting up paths, loading lookups,
        and initializing counters and patterns.

        Args:
            filepath (str, optional): The path to the loctime YAML file.
                                      Defaults to a predefined path if None is provided.
        Raises:
            FileNotFoundError: Raises an error if the specified YAML file does not exist.
        """
        if filepath is None:
            self.ceurws_path = os.path.expanduser("~/.ceurws")
            self.filepath = os.path.join(self.ceurws_path, "loctime.yaml")
        else:
            self.file_path = filepath
        self.lookups = self.load()
        self.setup()
        self.counters = {"4digit-year": Counter()}
        for reverse_pos in range(1, 8):
            self.counters[str(reverse_pos)] = Counter()
        for key in self.lookups:
            self.counters[key] = Counter()

        # Compile a pattern to match a 4-digit year
        self.year_pattern = re.compile(r"\b\d{4}\b")
        self.total_loctimes = 0

    def setup(self):
        """
        Prepares the parser by initializing multi-word handling and creating
        a modified version of the lookup dictionaries with keys as concatenated words.
        This method sets up the 'multi_word' and 'multi_word_lookups' dictionaries
        to facilitate the parsing process, especially for multi-word keys.
        """
        self.multi_word = {}
        for category, lookup in self.lookups.items():
            for key in lookup:
                if " " in key:
                    self.multi_word[key] = key.replace(" ", "_")

        # Initialize a dictionary derived from self.lookups with underscored keys
        self.multi_word_lookups = {}
        for category, lookup in self.lookups.items():
            self.multi_word_lookups[category] = {
                key.replace(" ", "_"): value for key, value in lookup.items()
            }

    def load(
        self,
    ) -> dict:
        """
        Loads the lookup data from the YAML file specified by the filepath attribute.

        This method attempts to open and read the YAML file, converting its contents
        into a dictionary. If the file is empty or does not exist, it returns an empty dictionary.

        Returns:
            dict: A dictionary representing the loaded data from the YAML file. If the file
                  is empty or non-existent, an empty dictionary is returned.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            yaml.YAMLError: If there is an error parsing the YAML file.
        """
        data_dict = {}
        if os.path.isfile(self.filepath) and os.path.getsize(self.filepath) > 0:
            with open(self.filepath, "r") as yaml_file:
                data_dict = yaml.safe_load(yaml_file)
        return data_dict

    def save(self):
        """
        Saves the current lookup dictionary to a YAML file.
        """
        os.makedirs(
            os.path.dirname(self.filepath), exist_ok=True
        )  # Ensure directory exists
        with open(self.filepath, "w", encoding="utf-8") as yaml_file:
            yaml.dump(
                self.lookups, yaml_file, default_flow_style=False, allow_unicode=True
            )

    def get_parts(self, loctime):
        """
        Splits the loctime string into parts and subparts, considering multi-word entries.

        Args:
            loctime (str): The loctime string to split.

        Returns:
            list: A list of parts and subparts.
        """
        # Replace known multi-word entries with their underscore versions
        for original, underscored in self.multi_word.items():
            loctime = loctime.replace(original, underscored)

        parts = loctime.split(",")  # First, split by comma
        all_parts = []
        for part in parts:
            # Further split each part by whitespace, considering underscore as part of the word
            subparts = part.strip().split()
            all_parts.extend(subparts)  # Add all subparts to the list

        return all_parts

    def parse(self, loctime: str):
        """
        Alternative parse of CEUR-WS loctimes using lookups

        Args:
            loctime (str): The loctime string to parse.

        """
        self.total_loctimes += 1
        lt_parts = self.get_parts(loctime)

        # Process each part of loctime
        for index, part in enumerate(lt_parts):
            part = part.strip()
            reverse_pos = len(lt_parts) - index  # Position from end

            found_in_lookup = False
            # Check against each lookup and update corresponding counter
            for (
                lookup_key,
                lookup_dict,
            ) in self.multi_word_lookups.items():
                if part in lookup_dict:
                    self.counters[lookup_key][part] += 1  # Increment the lookup counter
                    found_in_lookup = True
                    break  # Break if found, assuming part can't be in multiple lookups
            if not found_in_lookup:
                # Update counter for each part's position from end
                key = str(reverse_pos)
                if key in self.counters:
                    self.counters[key][part] += 1

            # Special handling for 4-digit years
            if index == len(lt_parts) - 1 and self.year_pattern.match(part):
                self.counters["4digit-year"][part] += 1

    def update_lookup_counts(self):
        """
        to be called  ffter processing all loctimes
        and updating counters update lookup dicts with new counts
        """
        for category, counter in self.counters.items():
            if category in self.lookups:
                for underscore_key, count in counter.items():
                    # Convert underscore_key back to space-separated key
                    original_key = underscore_key.replace("_", " ")
                    if original_key in self.lookups[category]:
                        # Update the count for the original key
                        self.lookups[category][original_key] += count
                    else:
                        # Initialize count for the original key
                        self.lookups[category][original_key] = count

    def create_pareto_analysis(self, level: int = 3, outof: int = 5):
        """
        Creates a Pareto analysis for each category in the lookups and returns
        the percentage table for the distribution across the specified levels.

        Args:
            level (int): The number of segments to divide the data into within the top "outof" parts.
            outof (int): 1 out of n value e.g. on level 1 we have 1:5 which leads to
            the original pareto 80:20 percent rule, on level 2 we have 80:(20=16:4) percent which is equivalent to 80/96 tresholds
            percent
            on level 3 we have 80:(20=16:4=(3.2:0.8) percent which leads to 80%,96%,99.2% thresholds
        """
        pareto_dict = {}
        for category, counter in self.counters.items():
            # Sort items by count in descending order
            sorted_items = counter.most_common()
            total = sum(counter.values())

            # Calculate segment thresholds based on the diminishing series
            thresholds = []
            threshold = 0
            for _ in range(1, level + 1):
                # current range to calculate out of for
                trange = 100 - threshold  # 100/80/96/99.2 ...
                # right side of range
                right_range = trange / outof  # 20/4/0.8 ...
                # left threshold is new threshold
                threshold = 100 - right_range
                thresholds.append(threshold)
            thresholds.append(100)

            segment_counts = {
                threshold: 0 for threshold in thresholds
            }  # Initialize count dict for each segment
            segment_cutoff = {
                threshold: 0 for threshold in thresholds
            }  # Initialize count dict for each segment
            tindex = 0
            current_threshold = thresholds[tindex]
            total_pc = 0
            # Calculate cumulative counts for each segment
            for _, count in sorted_items:
                item_percentage = count / total * 100
                if total_pc + item_percentage > current_threshold + 0.000000000001:
                    segment_cutoff[current_threshold] = count
                    tindex += 1
                    if tindex >= len(thresholds):
                        break
                    current_threshold = thresholds[tindex]
                total_pc += item_percentage
                segment_counts[current_threshold] += count

            pareto_dict[category] = segment_cutoff
        return pareto_dict


class PercentageTable:
    """
    A class for creating a table that displays values and their corresponding percentages of a total.

    Attributes:
        total (float): The total value used for calculating percentages.
        column_title (str): The title for the first column in the table.
        digits (int): The number of decimal places for rounding percentages.
        rows (list): A list of dictionaries representing rows in the table.
    """

    def __init__(self, column_title: str, total: float, digits: int):
        """
        Initializes the PercentageTable with a title for the column, a total value, and specified precision for percentages.

        Args:
            column_title (str): The title for the first column.
            total (float): The total value for calculating percentages.
            digits (int): The precision for percentage values.
        """
        self.total = total
        self.column_title = column_title
        self.digits = digits
        self.rows = [{self.column_title: "Total", "#": total, "%": 100.0}]

    def add_value(self, row_title: str, value: float):
        """
        Adds a row to the table with the given title and value, calculating the percentage of the total.

        Args:
            row_title (str): The title for the row.
            value (float): The value for the row, which is used to calculate its percentage of the total.
        """
        percentage = round((value / self.total) * 100, self.digits) if self.total else 0
        self.rows.append({self.column_title: row_title, "#": value, "%": percentage})

    def generate_table(self, tablefmt="grid") -> str:
        """
        Generates a string representation of the table using the tabulate library.

        Returns:
            str: The string representation of the table with headers and formatted rows.
        """
        if not self.rows:
            return ""
        tabulate_markup = tabulate(
            self.rows, headers="keys", tablefmt=tablefmt, floatfmt=f".{self.digits}f"
        )
        return tabulate_markup
