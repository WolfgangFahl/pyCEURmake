"""
Tests for ceurws.wd_contributions

See https://github.com/WolfgangFahl/pyCEURmake/issues/108

Created: 2026-05-06
@author: wf
"""
import tempfile
import unittest

from lodstorage.query import Endpoint

from ceurws.wd_contributions import (
    ContributionStats,
    HistoryRecord,
    WdClassSpec,
    WdContributionAnalyzer,
    WdContributionsConfig,
)
from tests.basetest import Basetest


class TestWdContributionsConfig(Basetest):
    """Local-only tests for the YAML-backed configuration and dataclasses.

    These tests do not hit any network service.
    """

    def setUp(self, debug=False, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)

    def testDefaultConfigLoads(self):
        """Default YAML resource loads and contains expected values."""
        cfg = WdContributionsConfig.default()
        self.assertEqual(cfg.endpoint_url, "https://query.wikidata.org/sparql")
        self.assertEqual(
            cfg.wikidata_entity_prefix, "http://www.wikidata.org/entity/"
        )
        self.assertIn("CEUR-WS", cfg.bot_users)
        self.assertEqual(
            set(cfg.source_of_truth),
            {"WolfgangFahl", "Tholzheim", "CEUR-WS"},
        )
        self.assertGreaterEqual(len(cfg.classes), 3)
        qids = {c.qid for c in cfg.classes}
        self.assertIn("Q1143604", qids)

    def testConfigYamlRoundTrip(self):
        """WdContributionsConfig round-trips through YAML."""
        cfg = WdContributionsConfig.default()
        yaml_str = cfg.to_yaml()
        cfg2 = WdContributionsConfig.from_yaml(yaml_str)
        self.assertEqual(cfg.endpoint_url, cfg2.endpoint_url)
        self.assertEqual(sorted(cfg.bot_users), sorted(cfg2.bot_users))
        self.assertEqual(
            sorted(cfg.source_of_truth), sorted(cfg2.source_of_truth)
        )
        self.assertEqual(len(cfg.classes), len(cfg2.classes))
        for a, b in zip(cfg.classes, cfg2.classes):
            self.assertEqual((a.qid, a.label, a.kind), (b.qid, b.label, b.kind))

    def testHistoryRecordRoundTrip(self):
        """HistoryRecord round-trips through dict and JSON via @lod_storable."""
        rec = HistoryRecord(
            qid="Q1",
            creator="Alice",
            editors=["Alice", "Bob"],
            edit_counts={"Alice": 3, "Bob": 1},
        )
        d = rec.to_dict()
        self.assertEqual(d["qid"], "Q1")
        self.assertEqual(d["edit_counts"]["Alice"], 3)
        rec2 = HistoryRecord.from_dict(d)
        self.assertEqual(rec, rec2)
        # JSON round-trip
        js = rec.to_json()
        rec3 = HistoryRecord.from_json(js)
        self.assertEqual(rec, rec3)

    def testContributionStatsRoundTrip(self):
        """ContributionStats round-trips through YAML via @lod_storable."""
        stats = ContributionStats(
            entity_class_qid="Q1143604",
            label="Proceedings",
            total_count=9896,
            analysed=9896,
            total_edits=50000,
            sot_edits=40000,
            community_edits=10000,
            distinct_community_editors=250,
            top_contributors=[("Sic19", 400), ("Fnielsen", 200)],
        )
        yaml_str = stats.to_yaml()
        stats2 = ContributionStats.from_yaml(yaml_str)
        self.assertEqual(stats.entity_class_qid, stats2.entity_class_qid)
        self.assertEqual(stats.total_edits, stats2.total_edits)
        self.assertEqual(stats.community_edits, stats2.community_edits)


class TestWdContributions(Basetest):
    """Tests for the Wikidata contribution analyzer."""

    _wikidata_available: bool | None = None

    def setUp(self, debug=False, profile=True):
        """
        set up test environment
        """
        Basetest.setUp(self, debug=debug, profile=profile)
        self.analyzer = WdContributionAnalyzer(debug=debug)
        # proper OO Endpoint construction — no module-level hack
        self.wikidata = Endpoint()
        self.wikidata.name = "wikidata"
        self.wikidata.endpoint = self.analyzer.endpoint_url
        self.wikidata.method = "POST"

    def _skip_if_no_wikidata(self) -> None:
        """Skip the current test if the Wikidata SPARQL endpoint is not reachable.

        The check is performed lazily (inside the test) rather than at import
        time, so that a 503 from Wikidata cannot break test discovery.
        Result is cached on the class so we probe the endpoint at most once
        per test run.
        """
        cls = type(self)
        if cls._wikidata_available is None:
            from lodstorage.sparql import SPARQL
            try:
                sparql = SPARQL(self.wikidata.endpoint, method=self.wikidata.method)
                sparql.query("SELECT * WHERE {} LIMIT 1")
                cls._wikidata_available = True
            except Exception as ex:
                if self.debug:
                    print(f"Wikidata unavailable: {ex}")
                cls._wikidata_available = False
        if not cls._wikidata_available:
            self.skipTest(f"SPARQL endpoint {self.wikidata.name} is unavailable")

    def testCounts(self):
        """Total count must be >= CEUR-WS count for Proceedings."""
        self._skip_if_no_wikidata()
        proceedings = "Q1143604"
        ceurws = self.analyzer.count_ceurws(proceedings)
        total = self.analyzer.count_total(proceedings)
        if self.debug:
            print(f"Proceedings CEUR-WS={ceurws} total={total}")
        self.assertGreater(ceurws, 3000, "Expected > 3000 CEUR-WS proceedings")
        self.assertGreaterEqual(total, ceurws)

    def testListQidsAll(self):
        """list_qids(kind='all') should return all items of the class."""
        self._skip_if_no_wikidata()
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
            set(self.analyzer.source_of_truth),
            {"WolfgangFahl", "Tholzheim", "CEUR-WS"},
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

    @unittest.skipIf(
        Basetest.inPublicCI(),
        "hits the live MediaWiki API; skip in public CI",
    )
    def testAnalyzeSmallSample(self):
        """End-to-end: analyze with a tiny sample (3 items per class)."""
        self._skip_if_no_wikidata()
        classes = self.analyzer.config.classes
        stats = self.analyzer.analyze(classes=classes, sample_size=3)
        self.assertEqual(len(stats), len(classes))
        for s in stats:
            self.assertGreater(s.total_count, 0)
            self.assertGreater(s.analysed, 0)
            self.assertGreaterEqual(s.total_edits, s.analysed)  # at least 1 rev each
            self.assertEqual(s.total_edits, s.sot_edits + s.community_edits)
        if self.debug:
            print(WdContributionAnalyzer.as_markdown_table(stats))
