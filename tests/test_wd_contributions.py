"""
Tests for ceurws.wd_contributions

See https://github.com/WolfgangFahl/pyCEURmake/issues/108

Created: 2026-05-06
@author: wf
"""

import os
import unittest

from lodstorage.query import Endpoint

from ceurws.wd_contributions import (
    DEFAULT_CLASSES,
    ContributionStats,
    HistoryRecord,
    WdContributionAnalyzer,
)
from tests.basetest import Basetest, requires_sparql_endpoint

WIKIDATA = Endpoint()
WIKIDATA.name = "wikidata"
WIKIDATA.endpoint = "https://query.wikidata.org/sparql"
WIKIDATA.method = "POST"


class TestWdContributions(Basetest):
    """Tests for the Wikidata contribution analyzer."""

    def setUp(self, debug=False, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.analyzer = WdContributionAnalyzer(debug=debug)

    @requires_sparql_endpoint(endpoint=WIKIDATA)
    def testCounts(self):
        """CEUR-WS count must be > 0 and <= total for Proceedings."""
        proceedings = "Q1143604"
        ceurws = self.analyzer.count_ceurws(proceedings)
        total = self.analyzer.count_total(proceedings)
        if self.debug:
            print(f"Proceedings CEUR-WS={ceurws} total={total}")
        self.assertGreater(ceurws, 3000, "Expected > 3000 CEUR-WS proceedings on Wikidata")
        self.assertGreaterEqual(total, ceurws)

    @requires_sparql_endpoint(endpoint=WIKIDATA)
    def testListCeurwsQids(self):
        """Listing should return well-formed QIDs."""
        qids = self.analyzer.list_ceurws_qids("Q1143604")
        self.assertGreater(len(qids), 100)
        for q in qids[:5]:
            self.assertTrue(q.startswith("Q"), f"unexpected QID: {q}")

    def testClassifyContributions(self):
        """Pure function: split records into community vs bot."""
        records = [
            HistoryRecord(qid="Q1", creator="PreScholarBot", editors=["PreScholarBot", "Alice"]),
            HistoryRecord(qid="Q2", creator="Alice", editors=["Alice"]),
            HistoryRecord(qid="Q3", creator="Bob", editors=["Bob", "PreScholarBot"]),
            HistoryRecord(qid="Q4", creator="DBLP-Bot", editors=["DBLP-Bot"]),
        ]
        community, bots, counter = self.analyzer.classify_contributions(records)
        self.assertEqual(community, 2)  # Alice + Bob
        self.assertEqual(bots, 2)  # PreScholarBot + DBLP-Bot
        self.assertEqual(community + bots, len(records))
        self.assertEqual(counter["Alice"], 1)

    def testRendering(self):
        """Markdown / LaTeX / JSON rendering of a fabricated stats list."""
        stats = [
            ContributionStats(
                entity_class_qid="Q1143604",
                label="Proceedings",
                ceurws_count=3500,
                total_count=4200,
                coverage_pct=83.33,
                sampled=10,
                community_count=4,
                bot_count=6,
                top_contributors=[("PreScholarBot", 6), ("Alice", 3), ("Bob", 1)],
            )
        ]
        md = WdContributionAnalyzer.as_markdown_table(stats)
        self.assertIn("| Class |", md)
        self.assertIn("Proceedings", md)
        self.assertIn("83.33", md)
        self.assertIn("PreScholarBot (6)", md)

        tex = WdContributionAnalyzer.as_latex_table(stats)
        self.assertIn(r"\begin{tabular}", tex)
        self.assertIn("Proceedings", tex)

        js = WdContributionAnalyzer.as_json(stats)
        self.assertIn('"label": "Proceedings"', js)

    @requires_sparql_endpoint(endpoint=WIKIDATA)
    @unittest.skipIf(
        Basetest.inPublicCI(),
        "fetch_history hits the live MediaWiki API; skip in public CI",
    )
    def testCoverageTableSmallSample(self):
        """End-to-end: produce a table for the default classes, sampled."""
        stats = self.analyzer.analyze(classes=DEFAULT_CLASSES, sample_size=3)
        self.assertEqual(len(stats), len(DEFAULT_CLASSES))
        for s in stats:
            self.assertGreater(s.ceurws_count, 0)
            self.assertGreaterEqual(s.total_count, s.ceurws_count)
            self.assertGreater(s.coverage_pct, 0.0)
            self.assertLessEqual(s.coverage_pct, 100.0)
            self.assertEqual(s.community_count + s.bot_count, s.sampled)
        if self.debug:
            print(WdContributionAnalyzer.as_markdown_table(stats))


if __name__ == "__main__":
    unittest.main()
