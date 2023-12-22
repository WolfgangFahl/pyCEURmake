"""
Created on 2023-12-22

@author: wf
"""
import json
import os
import re
from tests.basetest import Basetest
from collections import Counter
from tabulate import tabulate


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


class TestLoctimeParser(Basetest):
    """
    Test parsing loctime entries pages
    """

    def setUp(self, debug=True, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.ceurws_path = os.path.expanduser("~/.ceurws")
        self.volumes_path = os.path.join(self.ceurws_path, "volumes.json")
        self.volumes = self.get_volumes()

        self.lookups = {
            "month": {
                "January": 0,
                "February": 0,
                "March": 0,
                "April": 0,
                "May": 0,
                "June": 0,
                "July": 0,
                "August": 0,
                "September": 0,
                "October": 0,
                "November": 0,
                "December": 0,
                "Jan": 0,
                "Feb": 0,
                "Mar": 0,
                "Apr": 0,
                "May": 0,
                "Jun": 0,
                "Jul": 0,
                "Aug": 0,
                "Sep": 0,
                "Oct": 0,
                "Nov": 0,
                "Dec": 0,
            },
            "days": {
                "1": 0,
                "2": 0,
                "3": 0,
                "4": 0,
                "5": 0,
                "6": 0,
                "7": 0,
                "8": 0,
                "9": 0,
                "10": 0,
                "11": 0,
                "12": 0,
                "13": 0,
                "14": 0,
                "15": 0,
                "16": 0,
                "17": 0,
                "18": 0,
                "19": 0,
                "20": 0,
                "21": 0,
                "22": 0,
                "23": 0,
                "24": 0,
                "25": 0,
                "26": 0,
                "27": 0,
                "28": 0,
                "29": 0,
                "30": 0,
                "31": 0,
                "1st": 0,
                "2nd": 0,
                "3rd": 0,
                "4th": 0,
                "5th": 0,
                "6th": 0,
                "7th": 0,
                "8th": 0,
                "9th": 0,
                "10th": 0,
                "11th": 0,
                "12th": 0,
                "13th": 0,
                "14th": 0,
                "15th": 0,
                "16th": 0,
                "17th": 0,
                "18th": 0,
                "19th": 0,
                "20th": 0,
                "21st": 0,
                "22nd": 0,
                "23rd": 0,
                "24th": 0,
                "25th": 0,
                "26th": 0,
                "27th": 0,
                "28th": 0,
                "29th": 0,
                "30th": 0,
                "31st": 0,
            },
            "country": {
                "Italy": 335,
                "Germany": 213,
                "USA": 187,
                "Spain": 159,
                "Russia": 156,
                "France": 121,
                "Ukraine": 112,
                "Austria": 97,
                "Greece": 94,
                "Canada": 64,
                "UK": 63,
                "Portugal": 54,
                "China": 52,
                "Australia": 49,
                "The Netherlands": 47,
                "Netherlands": 0,
                "Brazil": 41,
                "Sweden": 39,
                "India": 36,
                "Belgium": 33,
                "United Kingdom": 32,
                "Slovenia": 32,
                "Japan": 31,
                "Norway": 29,
                "Poland": 27,
                "US": 5,
                "New Zealand": 0,
                "Denmark": 23,  # Added entry
                "Finland": 23,  # Added entry
                "Ireland": 22,  # Added entry
                "Switzerland": 21,  # Added entry
                "Cyprus": 18,  # Added entry
                "Turkey": 14,
                "Slovakia": 13,
                "Macedonia": 11,
                "Argentina": 11,
                "Serbia": 11,
                "Lithuania": 11,
                "United States": 0,
                "Mexico": 10,
                "Chile": 10,
                "Algeria": 10,
                "Estonia": 9,
                "Peru": 9,
                "Luxembourg": 8,
                "Latvia": 7,
                "Singapore": 6,
                "Scotland": 0,
                "Korea": 0,
                "Hungary": 0,
                "Israel": 0,
                "Czech Republic": 0,
                "Deutschland": 0,
                "Costa Rica": 0,
                "Cuba": 0,
                "Tunisia": 0,
                "Russian Federation": 0,
                "Bulgaria": 0,
                "Colombia": 0,
                "Brasil": 0,
                "Nigeria": 0,
                "Taiwan": 0,
                "Costa Rica": 0,
                "Island": 0,
                "Romania": 0,
                "Malaysia": 0,
                "Iceland": 0,
                "Croatia": 0,
                "Republic of Ireland": 0,
                "Republic of Korea": 0,
                "Slovak Republic": 0,
                "Italia": 0,
                "Panama": 0,
                "Algerie": 0,               
            },
            "region": {
                "Pennsylvania": 0,
                "Arizona": 0,
                "Wales": 0,
                "CA": 0,
                "British Columbia": 0,
                "Quebec": 0,
                "Texas": 0,
            },
            "city": {
                "Vienna": 66,
                "Wien": 0,
                "Moscow": 40,
                "Valencia": 34,
                "Barcelona": 32,
                "Kyiv": 32,
                "Rome": 30,
                "Lisbon": 27,
                "Sydney": 27,
                "Berlin": 26,
                "London": 26,
                "Amsterdam": 25,
                "Heraklion": 25,
                "Stockholm": 24,
                "Riva del Garda": 23,
                "Dublin": 20,
                "Paris": 19,
                "Ottawa": 19,
                "Crete": 18,
                "Pisa": 18,
                "Copenhagen": 18,
                "Yekaterinburg": 18,
                "Bari": 17,
                "Montpellier": 16,
                "California": 15,
                "Athens": 15,
                "Madrid": 15,
                "Kryvyi Rih": 15,
                "Graz": 14,
                "Samara": 14,
                "Hersonissos": 14,
                "Toulouse": 13,
                "Shanghai": 13,
                "Bonn": 13,
                "Boston": 13,
                "Beijing": 13,
                "Leuven": 13,
                "Rio de Janeiro": 13,
                "Prague": 13,
                "Melbourne": 13,
                "Lviv": 13,
                "Edinburgh": 11,
                "Bologna": 11,
                "Lyon": 11,
                "Eindhoven": 11,
                "Dresden": 11,
                "Kherson": 11,
                "Vancouver": 11,
                # Add additional cities as necessary
                # Existing cities from the prompt
                "Pisa": 2,
                "New York": 3,
                "New Dehli": 0,
                "New Orleans": 0,
                "New York City": 0,
                "New-York": 0,
                "Newcastle upon Tyne": 0,
                "Newcastle-upon-Tyne": 0,
                "Amsterdam": 2,
                "Potsdam": 10,
                "Turin": 10,
                "Leipzig": 10,
                "Kobe": 10,
                "Grenoble": 10,
                "Kharkiv": 10,
                "Padua": 9,
                "Rende": 9,
                "Florence": 9,
                "Buenos Aires": 0,
                "Essen": 9,
                "Bolzano": 9,
                "L'Aquila": 9,
                "Cagliari": 9,
                "Como": 9,
                "Saint-Malo": 9,
                "Bozen-Bolzano": 9,
                "Bergen": 9,
                "Skopje": 9,
                "Irkutsk": 9,
                "Hammamet": 8,
                "Oslo": 8,
                "Naples": 8,
                "Brussels": 8,
                "Trento": 8,
                "Tallinn": 8,
                "Riga": 8,
                "Thessaloniki": 8,
                "Catania": 8,
                "Torino": 8,
                "Porto": 8,
                "Portorož": 8,
                "Los Angeles": 0,
                "San Francisco": 0,
                "San Diego": 0,
                "San Jose": 0,
                "San José": 0,
                "San Sebastian": 0,
                "Palo Alto": 0,
                "Sao Paulo": 0,
                "Cape Town": 0,
                "Tokyo": 0,
                "Fort Lauderdale": 0,
                "Fort Wayne": 0,
                "Fortaleza": 0,
                "Newcastle": 0,
                "Hong Kong": 0,
                "Seattle": 0,
                "The Hague": 0,
                "Santiago de Compostela": 0,
                "Salt Lake City": 0,
                "Santa Fe": 0,
                "Santa Croce in Fossabande": 0,
                "Vladivostok": 1,
                "Kyoto": 1,
                "Ershovo": 1,
                "Hannover": 1,
                "Venice": 1,
                "Montenegro": 1,
                "Portoroz": 1,
                "Heidelberg": 1,
                "Ulm": 1,
                "La Certosa di Pontignano": 1,
                "La Clusaz": 1,
                "La Laguna": 1,
                "La Rochelle": 1,
                "Marina del Rey": 1,
                "Hamburg": 1,
                "Lima": 0,
                "Bremen": 1,
                "Aachen": 1,
                "Cuiabá": 1,
                "Milano": 1,
                "Kolkata": 1,
                "Roudnice": 1,
                "Sankt Augustin": 1,
                "Le Touquet": 1,
                "Stará Lesná": 1,
                "Aalborg": 1,
                "Ancona": 1,
                "Antwerp": 2,
                "Awaji": 1,
                "Bamberg": 1,
                "Bejaia": 1,
                "Bratislava": 2,
                "Bremerhaven": 1,
                "Budva": 1,
                "Cartagena": 1,
                "Castellaneta": 1,
                "Castiglione": 1,
                "Chania": 1,
                "Chennai": 3,
                "Chicago": 1,
                "Coimbra": 2,
                "Denver": 1,
                "Düsseldorf": 1,
                "Foster": 1,
                "Gjøvik": 1,
                "Haifa": 2,
                "Ilmenau": 2,
                "Jasna": 1,
                "Karlsruhe": 1,
                "Klagenfurt": 1,
                "Linz": 1,
                "Marettimo": 1,
                "Milan": 2,
                "Monterey": 2,
                "Munich": 1,
                "Münster": 2,
                "Neusiedl": 1,
                "Perugia": 1,
                "Petrozavodsk": 1,
                "Raleigh": 1,
                "Rostock": 1,
                "Santiago": 2,
                "Slavsko": 2,
                "Smrekovica": 1,
                "Stuttgart": 1,
                "Tampere": 1,
                "Tirana": 3,
                "Växjö": 1,
                "Xi'an": 1,
                "Yasar": 1,
                "Bouaghi": 1,
                "Bucharest": 1,
                "Canberra": 1,
                "Delhi": 1,
                "Doha": 1,
                "Ibaraki": 1,
                "Koper": 1,
                "Krems": 1,
                "Kusatsu": 1,
                "Linköping": 1,
                "Lucca": 1,
                "Malta": 1,
                "Nang": 1,
                "Pizzo": 1,
                "Plovdiv": 1,
                "Salamanca": 1,
                "Sofia": 1,
                "Southern": 1,
                "Timisoara": 1,
                "Utrecht": 1,
                "Vietri": 1,
                "Windsor": 1,
                "Winterthur": 1,
                "Worcester": 1,
                "Milton Keynes": 1,
                "Austin": 1,
                "Belfast": 1,
            },
        }
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

    def get_volumes(self):
        # Path to the volumes.json file
        # Ensure the file exists
        if not os.path.exists(self.volumes_path):
            return None
        # Read the JSON data
        with open(self.volumes_path, "r") as file:
            volumes_data = json.load(file)
        return volumes_data

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

    def test_loctime(self):
        """
        Test function to analyze loctime and count occurrences of parts.
        """
        # Initialize counters for reverse positions and specific lookups
        counters = {"4digit-year": Counter()}
        for reverse_pos in range(1, 8):
            counters[str(reverse_pos)] = Counter()
        for key in self.lookups:
            counters[key] = Counter()

        # Compile a pattern to match a 4-digit year
        year_pattern = re.compile(r"\b\d{4}\b")
        total_loctimes = 0

        for v in self.volumes:
            loctime = v["loctime"]
            if loctime:
                total_loctimes += 1
                lt_parts = self.get_parts(loctime)

                # Process each part of loctime
                for index, part in enumerate(lt_parts):
                    part = part.strip()
                    reverse_pos = len(lt_parts) - index  # Position from end

                    found_in_lookup = False
                    # Check against each lookup and update corresponding counter
                    for lookup_key, lookup_dict in self.multi_word_lookups.items():
                        if part in lookup_dict:
                            counters[lookup_key][
                                part
                            ] += 1  # Increment the lookup counter
                            found_in_lookup = True
                            break  # Break if found, assuming part can't be in multiple lookups
                    if not found_in_lookup:
                        # Update counter for each part's position from end
                        key = str(reverse_pos)
                        if key in counters:
                            counters[key][part] += 1

                    # Special handling for 4-digit years
                    if index == len(lt_parts) - 1 and year_pattern.match(part):
                        counters["4digit-year"][part] += 1

        # Generate and print the percentage table
        percentage_table = PercentageTable(
            column_title="Parts", total=total_loctimes, digits=2
        )
        for key, counter in counters.items():
            for part, count in counter.most_common(100):
                percentage_table.add_value(row_title=f"{key}: {part}", value=count)

        print(percentage_table.generate_table())
