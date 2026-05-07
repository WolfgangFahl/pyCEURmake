"""
Created on 2026-05-07

Command line interface for CEUR-WS Wikidata community contribution analysis.

@author: wf
"""

import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path

from basemkit.base_cmd import BaseCmd

from ceurws.version import Version
from ceurws.wd_contributions import WdContributionAnalyzer, WdContributionsConfig


class WdContributionsCmd(BaseCmd):
    """
    Command line handling for Wikidata community contribution analysis.
    """

    def __init__(self):
        super().__init__(version=Version(), description="CEUR-WS Wikidata community contribution analysis")

    def add_arguments(self, parser: ArgumentParser):
        """
        Add CLI arguments specific to the community contribution analysis.
        """
        super().add_arguments(parser)
        parser.add_argument(
            "--class",
            dest="class_qids",
            action="append",
            help="restrict analysis to this Wikidata class QID (repeatable). Default: all classes from config.",
        )
        parser.add_argument(
            "--config",
            help="path to a WdContributionsConfig YAML file (defaults to bundled resource)",
        )
        parser.add_argument(
            "--endpoint",
            help="override SPARQL endpoint URL from config",
        )
        parser.add_argument(
            "--format",
            choices=["markdown", "latex", "json"],
            default="markdown",
            help="output format for the statistics table [default: %(default)s]",
        )
        parser.add_argument(
            "--threshold",
            type=float,
            default=1.0,
            help="in plots, aggregate users below this percent of total into 'others' [default: %(default)s]",
        )
        parser.add_argument(
            "--plot",
            metavar="DIR",
            help="also render community-contribution pie charts (PNG) into DIR",
        )
        parser.add_argument(
            "--progress",
            action="store_true",
            help="show tqdm progress bars during revision fetch",
        )
        parser.add_argument(
            "--sample",
            type=int,
            metavar="N",
            help="cap analysis to N QIDs per class (useful for testing)",
        )

    def _load_analyzer(self, args: Namespace) -> WdContributionAnalyzer:
        """
        Build the analyzer from CLI args.
        """
        if args.config:
            config = WdContributionsConfig.load_from_yaml_file(args.config)
        else:
            config = WdContributionsConfig.default()
        if args.class_qids:
            wanted = set(args.class_qids)
            config.classes = [spec for spec in config.classes if spec.qid in wanted]
            if not config.classes:
                raise ValueError(f"no matching classes in config for QIDs: {sorted(wanted)}")
        analyzer = WdContributionAnalyzer(
            config=config,
            endpoint_url=args.endpoint,
            debug=args.debug,
        )
        return analyzer

    def handle_args(self, args: Namespace) -> bool:
        """
        Handle the parsed CLI arguments.
        """
        handled = super().handle_args(args)
        if handled:
            return True

        analyzer = self._load_analyzer(args)
        stats = analyzer.analyze(
            sample_size=args.sample,
            force=args.force,
            progress=args.progress or args.verbose or args.debug,
        )

        if args.format == "markdown":
            output = WdContributionAnalyzer.as_markdown_table(stats)
        elif args.format == "latex":
            output = WdContributionAnalyzer.as_latex_table(stats)
        else:
            output = WdContributionAnalyzer.as_json(stats)
        if not args.quiet:
            print(output)

        if args.plot:
            out_dir = Path(args.plot)
            written = analyzer.plot_all(
                out_dir=out_dir,
                force=args.force,
                progress=args.progress or args.verbose or args.debug,
                threshold=args.threshold,
            )
            if not args.quiet:
                for path in written:
                    print(f"wrote {path}")

        return True


def main(argv: list | None = None) -> int:
    """
    main call
    """
    cmd = WdContributionsCmd()
    exit_code = cmd.run(argv)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
