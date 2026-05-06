"""
Tests for ceurws.wd_contributions

See https://github.com/WolfgangFahl/pyCEURmake/issues/108

Created: 2026-05-06
@author: wf
"""

import unittest

from lodstorage.query import Endpoint

from ceurws.wd_contributions import (
    DEFAULT_CLASSES,
    DEFAULT_SOURCE_OF_TRUTH,
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
        """Total count must be >= CEUR-WS count for Proceedings."""
        proceedings = "Q1143604"
        ceurws = self.analyzer.count_ceurws(proceedings)
        total = self.analyzer.count_total(proceedings)
        if self.debug:
            print(f"Proceedings CEUR-WS={ceurws} total={total}")
        self.assertGreater(ceurws, 3000, "Expected > 3000 CEUR-WS proceedings")
        self.assertGreaterEqual(total, ceurws)

    @requires_sparql_endpoint(endpoint=WIKIDATA)
    def testListQidsAll(self):
        """list_qids(kind='all') should return all items of the class."""
        qids = self.analyzer.list_qids("Q1143604", kind="all")
        total = self.analyzer.count_total("Q1143604")
        self.assertGreater(len(qids), 5000)
        # SPARQL DISTINCT may slightly differ from COUNT; allow 1% margin
        self.assertAlmostEqual(len(qids), total, delta=max(50, total // 100))
        for q in qids[:5]:
            self.assertTrue(q.startswith("Q"), f"unexpected QID: {q}")

    def testClassifyEdits(self):
        """Pure function: split revisions into SoT vs community buckets."""
        records = [
            HistoryRecord(
                qid="Q1",
                edit_counts={"WolfgangFahl": 5, "Alice": 3, "Bob": 1},
            ),
            HistoryRecord(
                qid="Q2",
                edit_counts={"Tholzheim": 2, "CEUR-WS": 4, "Alice": 7},
            ),
        ]
        total, sot, community, counter = self.analyzer.classify_edits(records)
        # SoT: WF(5) + Th(2) + CEUR-WS(4) = 11
        # Community: Alice(3+7=10) + Bob(1) = 11
        self.assertEqual(total, 22)
        self.assertEqual(sot, 11)
        self.assertEqual(community, 11)
        self.assertEqual(counter["Alice"], 10)
        self.assertEqual(counter["Bob"], 1)
        self.assertNotIn("WolfgangFahl", counter)

    def testDefaultSoT(self):
        """The SoT set matches the specification from issue #108."""
        self.assertEqual(
            DEFAULT_SOURCE_OF_TRUTH,
            frozenset({"WolfgangFahl", "Tholzheim", "CEUR-WS"}),
        )

    def testRendering(self):
        """Markdown / LaTeX / JSON rendering of a fabricated stats list."""
        stats = [
            ContributionStats(
                entity_class_qid="Q1143604",
                label="Proceedings",
                total_count=9896,
                analysed=9896,
                total_edits=50000,
                sot_edits=40000,
                community_edits=10000,
                distinct_community_editors=250,
                top_contributors=[("Sic19", 400), ("Fnielsen", 200), ("KrBot", 150)],
            )
        ]
        md = WdContributionAnalyzer.as_markdown_table(stats)
        self.assertIn("| Class |", md)
        self.assertIn("Proceedings", md)
        self.assertIn("50000", md)
        self.assertIn("Sic19 (400)", md)

        tex = WdContributionAnalyzer.as_latex_table(stats)
        self.assertIn(r"\begin{tabular}", tex)
        self.assertIn("Proceedings", tex)
        self.assertIn("10000", tex)

        js = WdContributionAnalyzer.as_json(stats)
        self.assertIn('"label": "Proceedings"', js)
        self.assertIn('"community_edits": 10000', js)

    def testPlotDistributionEdits(self):
        """Local: render a community-only distribution chart from edit_counts."""
        import tempfile

        records = [
            HistoryRecord(
                qid="Q1",
                edit_counts={"WolfgangFahl": 40, "Alice": 20, "Bob": 15, "Rare1": 1},
            ),
            HistoryRecord(
                qid="Q2",
                edit_counts={"Tholzheim": 35, "CEUR-WS": 10, "Alice": 12, "Rare2": 2},
            ),
            HistoryRecord(
                qid="Q3",
                edit_counts={"Carol": 18, "Dan": 11, "Rare3": 1},
            ),
        ]
        with tempfile.TemporaryDirectory() as td:
            out = self.analyzer.plot_distribution(
                records,
                title="Test community edits",
                out_path=f"{td}/dist.png",
                threshold=10,
            )
            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 5_000)

    @requires_sparql_endpoint(endpoint=WIKIDATA)
    @unittest.skipIf(
        Basetest.inPublicCI(),
        "hits the live MediaWiki API; skip in public CI",
    )
    def testAnalyzeSmallSample(self):
        """End-to-end: analyze with a tiny sample (3 items per class)."""
        stats = self.analyzer.analyze(classes=DEFAULT_CLASSES, sample_size=3)
        self.assertEqual(len(stats), len(DEFAULT_CLASSES))
        for s in stats:
            self.assertGreater(s.total_count, 0)
            self.assertGreater(s.analysed, 0)
            self.assertGreaterEqual(s.total_edits, s.analysed)  # at least 1 rev each
            self.assertEqual(s.total_edits, s.sot_edits + s.community_edits)
        if self.debug:
            print(WdContributionAnalyzer.as_markdown_table(stats))


if __name__ == "__main__":
    unittest.main()
