"""
Created on 2023-12-22

@author: wf
"""
import json
import os

from ceurws.loctime import LoctimeParser, PercentageTable
from tests.basetest import Basetest


class TestLoctimeParser(Basetest):
    """
    Test parsing loctime entries pages
    """

    def setUp(self, debug=False, profile=True):
        """
        setUp the test case
        """
        Basetest.setUp(self, debug=debug, profile=profile)
        self.ceurws_path = os.path.expanduser("~/.ceurws")
        self.volumes_path = os.path.join(self.ceurws_path, "volumes.json")
        self.volumes = self.get_volumes()
        self.loctime_parser = LoctimeParser()

    def get_volumes(self):
        # Path to the volumes.json file
        # Ensure the file exists
        if not os.path.exists(self.volumes_path):
            return None
        # Read the JSON data
        with open(self.volumes_path, "r") as file:
            volumes_data = json.load(file)
        return volumes_data

    def test_loctime_parsing(self):
        """
        Test function to analyze loctime and count occurrences of parts.
        """
        ltp = self.loctime_parser
        for v in self.volumes:
            loctime = v["loctime"]
            if loctime:
                ltp.parse(loctime)

        ltp.update_lookup_counts()
        ltp.save()

        # Generate and print the percentage table
        percentage_table = PercentageTable(
            column_title="Parts", total=ltp.total_loctimes, digits=2
        )
        for key, counter in ltp.counters.items():
            for part, count in counter.most_common(100):
                percentage_table.add_value(row_title=f"{key}: {part}", value=count)

        print(percentage_table.generate_table())

        for reverse_pos in range(1, 8):
            counter = ltp.counters[str(reverse_pos)]
            print(f"== {reverse_pos} ({len(counter)}) ==")
            # Sorting the counter items by count in descending order
            for part, count in sorted(
                counter.items(), key=lambda item: item[1], reverse=True
            ):
                print(f"  {part}: {count}")

        pareto_dict = ltp.create_pareto_analysis(level=2)
        if self.debug:
            print(json.dumps(pareto_dict, indent=2))
        for category, pareto_range in pareto_dict.items():
            # Get the total count for this specific category
            counter = ltp.counters[category]
            total_category_count = sum(counter.values())

            # Create a percentage table for the current category
            percentage_table = PercentageTable(
                column_title=f"{category} pareto", total=total_category_count, digits=2
            )

            for threshold, count in pareto_range.items():
                percentage_table.add_value(f"{threshold:.1f}%", count)
            print(percentage_table.generate_table())
