"""
Created on 2024-02-22

@author: wf
"""
import sys
from argparse import ArgumentParser
from dataclasses import asdict

from ngwidgets.cmd import WebserverCmd
from tabulate import tabulate
from tqdm import tqdm

from ceurws.ceur_ws import VolumeManager
from ceurws.namedqueries import NamedQueries
from ceurws.webserver import CeurWsWebServer
from ceurws.wikidatasync import WikidataSync


class CeurWsCmd(WebserverCmd):
    """
    command line handling for CEUR-WS Volume browser
    """

    def __init__(self):
        """
        constructor
        """
        config = CeurWsWebServer.get_config()
        WebserverCmd.__init__(self, config, CeurWsWebServer, DEBUG)
        pass

    def getArgParser(self, description: str, version_msg) -> ArgumentParser:
        """
        override the default argparser call
        """
        parser = super().getArgParser(description, version_msg)
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="force update [default: %(default)s]",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="list all volumes [default: %(default)s]",
        )
        parser.add_argument(
            "-rc",
            "--recreate",
            action="store_true",
            help="recreate caches e.g. volume table",
        )
        parser.add_argument(
            "-den",
            "--dblp_endpoint_name",
            help="name of dblp endpoint to use %(default)s",
            default="qlever-dblp",
        )
        parser.add_argument(
            "-wen",
            "--wikidata_endpoint_name",
            help="name of wikidata endpoint to use %(default)s",
            default="wikidata",
        )
        parser.add_argument(
            "-wdu",
            "--wikidata_update",
            action="store_true",
            help="update tables from wikidata",
        )
        parser.add_argument(
            "-dbu", "--dblp_update", action="store_true", help="update dblp cache"
        )
        parser.add_argument(
            "-nq",
            "--namedqueries",
            action="store_true",
            help="generate named queries [default: %(default)s]",
        )
        return parser

    def handle_args(self) -> bool:
        """
        handle the command line arguments
        """
        args = self.args
        if args.namedqueries:
            nq = NamedQueries()
            yaml = nq.toYaml()
            print(yaml)
        if args.list:
            manager = VolumeManager()
            manager.loadFromBackup()
            for volume in manager.getList():
                print(volume)
        if args.recreate:
            manager = VolumeManager()
            manager.recreate(progress=True)
        if args.wikidata_update:
            wdsync = WikidataSync.from_args(args)
            wdsync.update(withStore=True)
        if args.dblp_update:
            wdsync = WikidataSync.from_args(args)
            endpoint = wdsync.dbpEndpoint
            print(f"updating dblp cache from SPARQL endpoint {endpoint.sparql.url}")
            # Instantiate the progress bar
            pbar = tqdm(total=len(wdsync.dbpEndpoint.cache_functions))
            for _step, (cache_name, cache_function) in enumerate(
                endpoint.cache_functions.items(), start=1
            ):
                # Call the corresponding function to refresh cache data
                cache_function(force_query=args.force)
                # Update the progress bar description with the cache name and increment
                pbar.set_description(f"{cache_name} updated ...")

                # Update the progress bar manually
                pbar.update(1)  # Increment the progress bar by 1 for each iteration

            # Close the progress bar after the loop
            pbar.close()
            table_data = []
            for _step, (cache_name, cache_function) in enumerate(
                endpoint.cache_functions.items(), start=1
            ):
                info = endpoint.json_cache_manager.get_cache_info(cache_name)
                table_data.append(asdict(info))
            table = tabulate(table_data, headers="keys", tablefmt="grid")
            print(table)
            pass
        handled = super().handle_args()
        return handled


def main(argv: list = None):
    """
    main call
    """
    cmd = CeurWsCmd()
    exit_code = cmd.cmd_main(argv)
    return exit_code


DEBUG = 0
if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-d")
    sys.exit(main())
