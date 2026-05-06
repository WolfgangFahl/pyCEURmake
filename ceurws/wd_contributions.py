"""
CEUR-WS Wikidata community contribution analysis.

Adapted from the prototype at
https://cr.bitplan.com/index.php/CEUR-WS_Wikidata_Contributions

Computes, per Wikidata entity class:
  - number of CEUR-WS entities (instance-of class AND P179 -> Q27230297)
  - total number of entities of that class on Wikidata
  - CEUR-WS coverage percentage
  - number of community vs bot edits (creator + revision history)
  - top contributors

See: https://github.com/WolfgangFahl/pyCEURmake/issues/108

Created: 2026-05-06
@author: wf
"""

from __future__ import annotations

import dataclasses
import json
import os
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import requests
from lodstorage.query import QueryManager
from lodstorage.rate_limiter import RateLimiter
from lodstorage.sparql import SPARQL
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ceurws.config import CEURWS

# Wikidata QIDs of bot accounts that mass-created CEUR-WS entries.
# Anything outside this set is treated as a community contribution.
DEFAULT_BOT_USERS: frozenset[str] = frozenset(
    {
        "CEUR-WS",        # primary CEUR-WS bot account
        "PreScholarBot",
        "DBLP-Bot",
        "KrBot",          # generic Wikidata maintenance bot
    }
)

# "Source of truth" users: the three accounts whose edits we treat as the
# bot / maintainer baseline. Edits by anyone else are "community" edits.
DEFAULT_SOURCE_OF_TRUTH: frozenset[str] = frozenset(
    {"WolfgangFahl", "Tholzheim", "CEUR-WS"}
)

# Default classes analysed.
# Each entry is (class_qid, label, kind) where kind is:
#   - "proceedings": item itself has wdt:P179 wd:Q27230297
#   - "event":       item is reachable as ?proc wdt:P4745 ?item from a CEUR-WS proceeding
#   - "all":         any item with wdt:P31 wd:<class>, no CEUR-WS filter
DEFAULT_CLASSES: list[tuple[str, str, str]] = [
    ("Q1143604", "Proceedings", "all"),
    ("Q2020153", "Academic conference", "all"),
    ("Q40444998", "Academic workshop", "all"),
]

WIKIDATA_ENTITY_PREFIX = "http://www.wikidata.org/entity/"


@dataclass
class HistoryRecord:
    """One QID's contributor footprint."""

    qid: str
    creator: str | None = None
    editors: list[str] = field(default_factory=list)
    # Per-user revision count for this item (edits attributable to each user).
    # Empty when only creator/editors were collected.
    edit_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "HistoryRecord":
        return cls(
            qid=d["qid"],
            creator=d.get("creator"),
            editors=list(d.get("editors", [])),
            edit_counts=dict(d.get("edit_counts", {})),
        )


@dataclass
class ContributionStats:
    """Aggregated per-class contribution statistics."""

    entity_class_qid: str
    label: str
    # item counts
    total_count: int        # total Wikidata items of this class
    analysed: int           # items for which we collected revisions
    # edit counts (revision-level)
    total_edits: int
    sot_edits: int
    community_edits: int
    distinct_community_editors: int
    top_contributors: list[tuple[str, int]]    # community-only top editors

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


class WdContributionAnalyzer:
    """
    Analyse CEUR-WS contributions to Wikidata.

    Heavy operations (history fetch over MediaWiki API) are cached on disk under
    ``~/.ceurws/wd_contributions/``.
    """

    def __init__(
        self,
        endpoint_url: str = "https://query.wikidata.org/sparql",
        bot_users: Iterable[str] | None = None,
        source_of_truth: Iterable[str] | None = None,
        cache_dir: Path | None = None,
        sleep_every: int = 100,
        sleep_seconds: int = 30,
        debug: bool = False,
    ):
        """
        Args:
            endpoint_url: Wikidata SPARQL endpoint URL.
            bot_users: usernames considered bots; defaults to ``DEFAULT_BOT_USERS``.
            source_of_truth: usernames whose edits represent the bot/maintainer
                baseline; their revisions are counted separately from community
                revisions. Defaults to ``DEFAULT_SOURCE_OF_TRUTH``.
            cache_dir: directory for JSON caches (default ``$CEURWS.CACHE_DIR/wd_contributions``).
            sleep_every: throttle the MediaWiki API every N pages.
            sleep_seconds: seconds to sleep when throttling.
            debug: verbose logging.
        """
        self.endpoint_url = endpoint_url
        self.sparql = SPARQL(endpoint_url)
        self.bot_users: set[str] = set(bot_users) if bot_users is not None else set(DEFAULT_BOT_USERS)
        self.source_of_truth: set[str] = (
            set(source_of_truth) if source_of_truth is not None else set(DEFAULT_SOURCE_OF_TRUTH)
        )
        self.cache_dir = cache_dir or (CEURWS.CACHE_DIR / "wd_contributions")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.sleep_every = sleep_every
        self.sleep_seconds = sleep_seconds
        self.debug = debug
        self.qm = self._load_query_manager()
        self._ensure_wikidata_wikiuser()

    @staticmethod
    def _ensure_wikidata_wikiuser() -> None:
        """
        Ensure that wikibot3rd has a ``wikidata`` wikiId configured for
        anonymous read-only access (no password). Creates a minimal ini file
        on first use; existing config is left untouched.
        """
        try:
            from wikibot3rd.wikiuser import WikiUser
        except ImportError:  # pragma: no cover
            return
        ini_path = Path(WikiUser.iniFilePath("wikidata"))
        if ini_path.exists():
            return
        ini_path.parent.mkdir(parents=True, exist_ok=True)
        ini_path.write_text(
            "# auto-generated by ceurws.wd_contributions\n"
            "wikiId=wikidata\n"
            "url=https://www.wikidata.org\n"
            "scriptPath=/w/\n"
            "version=MediaWiki 1.42.0\n"
            "user=\n"
            "is_smw=False\n"
        )

    # ------------------------------------------------------------------ queries

    @staticmethod
    def _load_query_manager() -> QueryManager:
        """Load the bundled CEUR-WS named queries."""
        path = os.path.dirname(__file__)
        q_yaml = f"{path}/resources/queries/ceurws.yaml"
        return QueryManager(lang="sparql", queriesPath=q_yaml)

    def _scalar_count(self, query_name: str, class_qid: str) -> int:
        """Run a named COUNT query and return the integer result."""
        query = self.qm.queriesByName[query_name]
        sparql_str = query.query.format(class_qid=class_qid)
        rows = self.sparql.queryAsListOfDicts(sparql_str)
        if not rows:
            return 0
        return int(rows[0].get("count", 0))

    @staticmethod
    def _build_session() -> requests.Session:
        """
        Build a requests.Session with a descriptive UA and urllib3 Retry
        honouring ``Retry-After`` on 429 / 5xx responses.
        """
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": (
                    "pyCEURmake/wd_contributions "
                    "(https://github.com/WolfgangFahl/pyCEURmake)"
                )
            }
        )
        retry = Retry(
            total=8,
            backoff_factor=2.0,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET"]),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def count_ceurws(self, class_qid: str, kind: str = "proceedings") -> int:
        """Number of CEUR-WS-affiliated entities of the given class."""
        query_name = "CeurwsEventEntityCount" if kind == "event" else "CeurwsEntityCount"
        return self._scalar_count(query_name, class_qid)

    def count_total(self, class_qid: str) -> int:
        """Total number of entities of the given class on Wikidata."""
        return self._scalar_count("TotalEntityCount", class_qid)

    def list_qids(self, class_qid: str, kind: str = "all") -> list[str]:
        """
        Return QIDs for the given class.

        kind:
          - "all": every item with wdt:P31 wd:<class>
          - "proceedings": CEUR-WS proceedings (P179 filter)
          - "event": CEUR-WS-linked events (reverse P4745 from a CEUR-WS proceeding)
        """
        if kind == "all":
            query_name = "AllEntityList"
        elif kind == "event":
            query_name = "CeurwsEventEntityList"
        else:
            query_name = "CeurwsEntityList"
        query = self.qm.queriesByName[query_name]
        sparql_str = query.query.format(class_qid=class_qid)
        rows = self.sparql.queryAsListOfDicts(sparql_str)
        qids: list[str] = []
        for row in rows:
            uri = row.get("item", "")
            if uri.startswith(WIKIDATA_ENTITY_PREFIX):
                qids.append(uri[len(WIKIDATA_ENTITY_PREFIX):])
        return qids

    # Backwards-compatible alias
    def list_ceurws_qids(self, class_qid: str, kind: str = "proceedings") -> list[str]:
        return self.list_qids(class_qid, kind=kind)

    # --------------------------------------------------------------- history

    def _cache_path(self, class_qid: str) -> Path:
        return self.cache_dir / f"history_{class_qid}.json"

    def load_cache(self, class_qid: str) -> dict[str, HistoryRecord]:
        path = self._cache_path(class_qid)
        if not path.exists():
            return {}
        try:
            with path.open("r") as fp:
                raw = json.load(fp)
        except (OSError, json.JSONDecodeError):
            return {}
        return {qid: HistoryRecord.from_dict(d) for qid, d in raw.items()}

    def save_cache(self, class_qid: str, records: dict[str, HistoryRecord]) -> None:
        path = self._cache_path(class_qid)
        with path.open("w") as fp:
            json.dump(
                {qid: r.to_dict() for qid, r in records.items()},
                fp,
                indent=2,
            )

    def fetch_history(
        self,
        qids: list[str],
        class_qid: str,
        max_items: int | None = None,
        force: bool = False,
    ) -> list[HistoryRecord]:
        """
        Fetch creator + editors for each QID; results are cached on disk.

        Args:
            qids: QIDs to query.
            class_qid: used as cache namespace.
            max_items: cap on total fetched (useful for tests).
            force: ignore cache and refetch.

        Returns:
            list of HistoryRecord, one per processed QID.
        """
        # Imported lazily so the module can be imported without the dep present
        # (e.g. when only counts are needed).
        from wikibot3rd.pagehistory import PageHistory

        cache = {} if force else self.load_cache(class_qid)
        to_fetch = [q for q in qids if q not in cache]
        if max_items is not None:
            to_fetch = to_fetch[:max_items]

        total = len(to_fetch)
        for i, qid in enumerate(to_fetch, 1):
            if self.sleep_every and i % self.sleep_every == 0:
                if self.debug:
                    print(f"[wd_contributions] throttle: sleep {self.sleep_seconds}s")
                time.sleep(self.sleep_seconds)
            try:
                ph = PageHistory(pageTitle=qid, wikiId="wikidata")
                editors = sorted({rev.user for rev in ph.revisions if rev.user})
                cache[qid] = HistoryRecord(
                    qid=qid,
                    creator=ph.getFirstUser(),
                    editors=editors,
                )
                if self.debug:
                    print(f"[wd_contributions] {i:04}/{total:04} {qid} ok")
            except Exception as e:  # pragma: no cover - network defensive
                if self.debug:
                    print(f"[wd_contributions] {i:04}/{total:04} {qid} failed: {e}")

        self.save_cache(class_qid, cache)
        # Return only records for the requested qids (in original order)
        return [cache[q] for q in qids if q in cache]

    def fetch_creators_batched(
        self,
        qids: list[str],
        class_qid: str,
        batch_size: int = 50,
        force: bool = False,
        api_url: str = "https://www.wikidata.org/w/api.php",
        calls_per_minute: int = 200,
    ) -> list[HistoryRecord]:
        """
        Fast path: fetch only the *creator* of each item via
        MediaWiki ``action=query&prop=revisions&rvdir=newer&rvlimit=1``.

        The MediaWiki API rejects multi-page queries combined with
        ``rvdir``/``rvlimit``, so we issue one request per QID. Request rate
        is capped via ``lodstorage.rate_limiter.RateLimiter`` to stay under
        Wikimedia's unauthenticated read limit (default 500/min).

        ``batch_size`` controls cache-flush granularity (every N requests).

        Returns HistoryRecord with ``editors=[]`` (not collected; use
        ``fetch_history`` for full editor list).
        """
        cache = {} if force else self.load_cache(class_qid)
        to_fetch = [q for q in qids if q not in cache]
        total = len(to_fetch)
        session = self._build_session()

        limiter = RateLimiter(calls_per_minute=calls_per_minute)

        @limiter.rate_limited
        def _fetch_one(qid: str) -> tuple[str, str | None]:
            params = {
                "action": "query",
                "format": "json",
                "prop": "revisions",
                "rvprop": "user|timestamp",
                "rvdir": "newer",
                "rvlimit": 1,
                "titles": qid,
                "formatversion": 2,
            }
            resp = session.get(api_url, params=params, timeout=30)
            resp.raise_for_status()
            pages = resp.json().get("query", {}).get("pages", [])
            if not pages:
                return qid, None
            revs = pages[0].get("revisions", [])
            return qid, (revs[0].get("user") if revs else None)

        for i, qid in enumerate(to_fetch, 1):
            try:
                _, creator = _fetch_one(qid)
                cache[qid] = HistoryRecord(qid=qid, creator=creator, editors=[])
            except Exception as e:  # pragma: no cover - network defensive
                if self.debug:
                    print(f"[wd_contributions] {qid} failed: {e}")

            if self.debug and i % batch_size == 0:
                print(f"[wd_contributions] creators {i:5d}/{total:5d}")
            if i % (batch_size * 10) == 0:
                self.save_cache(class_qid, cache)

        if self.debug and total:
            print(f"[wd_contributions] creators {total:5d}/{total:5d} done")
        self.save_cache(class_qid, cache)
        return [cache[q] for q in qids if q in cache]

    def fetch_revisions_full(
        self,
        qids: list[str],
        class_qid: str,
        force: bool = False,
        api_url: str = "https://www.wikidata.org/w/api.php",
        calls_per_minute: int = 200,
        progress_every: int = 25,
    ) -> list[HistoryRecord]:
        """
        Fetch *every* revision (user + timestamp) for each QID with
        ``rvcontinue`` pagination, populating ``HistoryRecord.edit_counts``
        (user -> revision count) and ``creator`` (earliest revision user).

        Rate-limited via ``lodstorage.RateLimiter`` and retried on 429/5xx
        via ``urllib3.Retry`` honouring ``Retry-After``.

        Cached on disk. Items already present in the cache with non-empty
        ``edit_counts`` are skipped unless ``force=True``.
        """
        cache = {} if force else self.load_cache(class_qid)
        to_fetch = [
            q for q in qids if q not in cache or not cache[q].edit_counts
        ]
        total = len(to_fetch)
        session = self._build_session()
        limiter = RateLimiter(calls_per_minute=calls_per_minute)

        @limiter.rate_limited
        def _fetch_page(qid: str, rvcontinue: str | None) -> dict:
            params = {
                "action": "query",
                "format": "json",
                "prop": "revisions",
                "rvprop": "user|timestamp",
                "rvlimit": "max",
                "titles": qid,
                "formatversion": 2,
            }
            if rvcontinue:
                params["rvcontinue"] = rvcontinue
            resp = session.get(api_url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()

        for i, qid in enumerate(to_fetch, 1):
            try:
                edit_counts: Counter = Counter()
                earliest_user: str | None = None
                earliest_ts: str | None = None
                rvcontinue: str | None = None
                while True:
                    data = _fetch_page(qid, rvcontinue)
                    pages = data.get("query", {}).get("pages", [])
                    if not pages:
                        break
                    revs = pages[0].get("revisions", []) or []
                    for rev in revs:
                        user = rev.get("user")
                        ts = rev.get("timestamp")
                        if user:
                            edit_counts[user] += 1
                        if ts and (earliest_ts is None or ts < earliest_ts):
                            earliest_ts = ts
                            earliest_user = user
                    cont = data.get("continue", {})
                    rvcontinue = cont.get("rvcontinue")
                    if not rvcontinue:
                        break
                cache[qid] = HistoryRecord(
                    qid=qid,
                    creator=earliest_user,
                    editors=sorted(edit_counts.keys()),
                    edit_counts=dict(edit_counts),
                )
            except Exception as e:  # pragma: no cover - network defensive
                if self.debug:
                    print(f"[wd_contributions] {qid} failed: {e}")

            if self.debug and i % progress_every == 0:
                print(f"[wd_contributions] revisions {i:5d}/{total:5d}")
            if i % (progress_every * 10) == 0:
                self.save_cache(class_qid, cache)

        if self.debug and total:
            print(f"[wd_contributions] revisions {total:5d}/{total:5d} done")
        self.save_cache(class_qid, cache)
        return [cache[q] for q in qids if q in cache]

    # --------------------------------------------------------------- analysis

    def classify_contributions(
        self,
        records: list[HistoryRecord],
    ) -> tuple[int, int, Counter]:
        """
        (legacy) Split records into community vs bot based on the *creator*
        of the item.

        Returns:
            (community_count, bot_count, Counter(creator -> count))
        """
        creators = Counter(r.creator or "<unknown>" for r in records)
        community = sum(c for u, c in creators.items() if u not in self.bot_users)
        bots = sum(c for u, c in creators.items() if u in self.bot_users)
        return community, bots, creators

    def classify_edits(
        self,
        records: list[HistoryRecord],
        source_of_truth: Iterable[str] | None = None,
    ) -> tuple[int, int, int, Counter]:
        """
        Split revisions into source-of-truth vs community buckets.

        Args:
            records: HistoryRecord list with populated ``edit_counts``.
            source_of_truth: user set to treat as SoT; defaults to
                ``self.source_of_truth``.

        Returns:
            (total_edits, sot_edits, community_edits, community_editor_counter)
        """
        sot = set(source_of_truth) if source_of_truth is not None else self.source_of_truth
        total = 0
        sot_edits = 0
        community_counter: Counter = Counter()
        for rec in records:
            for user, count in rec.edit_counts.items():
                total += count
                if user in sot:
                    sot_edits += count
                else:
                    community_counter[user] += count
        community_edits = total - sot_edits
        return total, sot_edits, community_edits, community_counter

    def analyze(
        self,
        classes: list[tuple[str, str, str]] | None = None,
        sample_size: int | None = None,
        force: bool = False,
        progress: bool | None = None,
    ) -> list[ContributionStats]:
        """
        Compute ContributionStats for each (class_qid, label, kind) tuple.

        Fetches the **full revision history** of every item and classifies
        each revision as source-of-truth (``self.source_of_truth``) or
        community.

        Args:
            classes: list of (qid, label, kind); defaults to ``DEFAULT_CLASSES``.
                ``kind`` is "all" (no CEUR-WS filter, default in DEFAULT_CLASSES),
                "proceedings" (P179-based) or "event" (reverse P4745).
            sample_size: if set, only analyse this many QIDs per class
                (useful for tests).
            force: ignore the on-disk cache.
            progress: print progress (defaults to self.debug).
        """
        if progress is None:
            progress = self.debug
        classes = classes or DEFAULT_CLASSES
        results: list[ContributionStats] = []
        for class_qid, label, kind in classes:
            total_count = self.count_total(class_qid)
            qids = self.list_qids(class_qid, kind=kind)
            if sample_size is not None:
                qids = qids[:sample_size]

            records = self.fetch_revisions_full(
                qids, class_qid=class_qid, force=force
            )
            total_edits, sot_edits, community_edits, community_counter = (
                self.classify_edits(records)
            )
            top = community_counter.most_common(10)

            results.append(
                ContributionStats(
                    entity_class_qid=class_qid,
                    label=label,
                    total_count=total_count,
                    analysed=len(records),
                    total_edits=total_edits,
                    sot_edits=sot_edits,
                    community_edits=community_edits,
                    distinct_community_editors=len(community_counter),
                    top_contributors=top,
                )
            )
        return results

    # --------------------------------------------------------------- rendering

    @staticmethod
    def as_markdown_table(stats: list[ContributionStats]) -> str:
        header = (
            "| Class | QID | Items | Analysed | Total edits | SoT edits | "
            "Community edits | Distinct community editors | Top community editors |\n"
            "|---|---|---:|---:|---:|---:|---:|---:|---|\n"
        )
        rows = []
        for s in stats:
            top = ", ".join(f"{u} ({c})" for u, c in s.top_contributors)
            rows.append(
                f"| {s.label} | {s.entity_class_qid} | {s.total_count} | {s.analysed} "
                f"| {s.total_edits} | {s.sot_edits} | {s.community_edits} "
                f"| {s.distinct_community_editors} | {top} |"
            )
        return header + "\n".join(rows) + "\n"

    @staticmethod
    def as_latex_table(stats: list[ContributionStats]) -> str:
        lines = [
            r"\begin{tabular}{lrrrrrrl}",
            r"\hline",
            r"Class & Items & Analysed & Total edits & SoT edits & "
            r"Community edits & Distinct community editors & Top community editors \\",
            r"\hline",
        ]
        for s in stats:
            top = ", ".join(f"{u} ({c})" for u, c in s.top_contributors)
            top_escaped = top.replace("_", r"\_")
            label_escaped = s.label.replace("_", r"\_")
            lines.append(
                f"{label_escaped} & {s.total_count} & {s.analysed} "
                f"& {s.total_edits} & {s.sot_edits} & {s.community_edits} "
                f"& {s.distinct_community_editors} & {top_escaped} \\\\"
            )
        lines += [r"\hline", r"\end{tabular}"]
        return "\n".join(lines) + "\n"

    @staticmethod
    def as_json(stats: list[ContributionStats]) -> str:
        return json.dumps([s.to_dict() for s in stats], indent=2)

    # --------------------------------------------------------------- plotting

    def plot_distribution(
        self,
        records: list[HistoryRecord],
        title: str,
        out_path: Path | str,
        threshold: int = 10,
        exclude_users: Iterable[str] | None = None,
        mode: str = "edits",
        figsize: tuple[float, float] = (8.0, 6.0),
        dpi: int = 150,
    ) -> Path:
        """
        Render a contribution pie chart.

        Args:
            records: HistoryRecord list.
            title: chart title.
            out_path: PNG output path.
            threshold: users with fewer than this many contributions are
                aggregated into "others".
            exclude_users: users to drop entirely before plotting (defaults
                to ``self.source_of_truth`` so the chart shows *community*
                contributions only).
            mode: "edits" (sum ``edit_counts`` per user; default) or
                "creators" (count items created per user — legacy behaviour).
            figsize/dpi: matplotlib figure params.

        Returns:
            Path to the written PNG.
        """
        # lazy import so the module can be imported headless
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if exclude_users is None:
            exclude_users = self.source_of_truth
        exclude = set(exclude_users)

        counter: Counter = Counter()
        if mode == "edits":
            for r in records:
                for user, count in r.edit_counts.items():
                    if user and user not in exclude:
                        counter[user] += count
        else:  # "creators"
            for r in records:
                if r.creator and r.creator not in exclude:
                    counter[r.creator] += 1

        total_contribs = sum(counter.values())
        distribution: dict[str, int] = {"others": 0}
        for user, count in counter.most_common():
            if count < threshold:
                distribution["others"] += count
            else:
                distribution[user] = count
        if distribution["others"] == 0:
            distribution.pop("others")
        if not distribution:
            # nothing to plot; still emit a placeholder so callers see a file
            distribution = {"(no data)": 1}

        labels = list(distribution.keys())
        sizes = list(distribution.values())

        fig, ax = plt.subplots(figsize=figsize)
        ax.pie(
            sizes,
            labels=labels,
            autopct="%1.1f%%",
            startangle=90,
            textprops={"fontsize": 9},
        )
        ax.axis("equal")
        subtitle = (
            f"items={len(records)}, contributions={total_contribs}, "
            f"distinct editors={len(counter)}"
        )
        plt.title(f"{title}\n({subtitle})")
        plt.tight_layout()
        fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
        plt.close(fig)
        return out_path

    def plot_all(
        self,
        out_dir: Path | str,
        classes: list[tuple[str, str, str]] | None = None,
        force: bool = False,
        prefix: str = "distribution_of_",
        suffix: str = "_community_editors.png",
        mode: str = "edits",
    ) -> list[Path]:
        """
        Generate one community-contribution pie per entity class and write
        them as PNGs into ``out_dir``.

        Uses the full revision history (``fetch_revisions_full``) and
        excludes ``self.source_of_truth`` users from the chart so that
        genuine community activity is visible.

        Returns the list of written paths.
        """
        classes = classes or DEFAULT_CLASSES
        out_dir = Path(out_dir)
        written: list[Path] = []
        for class_qid, label, kind in classes:
            qids = self.list_qids(class_qid, kind=kind)
            records = self.fetch_revisions_full(
                qids, class_qid=class_qid, force=force
            )
            slug = label.lower().replace(" ", "_")
            out_path = out_dir / f"{prefix}{slug}{suffix}"
            self.plot_distribution(
                records,
                title=f"Community Editors of {label} (SoT excluded)",
                out_path=out_path,
                mode=mode,
            )
            written.append(out_path)
            if self.debug:
                print(f"[wd_contributions] wrote {out_path} ({len(records)} items)")
        return written
