"""
Created on 2023-02-20

@author: wf
"""
import sys
import traceback
import webbrowser
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from dataclasses import asdict
from tabulate import tabulate
from tqdm import tqdm

# import after app!
from jpcore.justpy_app import JustpyServer

from ceurws.ceur_ws import VolumeManager
from ceurws.namedqueries import NamedQueries
from ceurws.version import Version
from ceurws.wikidatasync import WikidataSync


def getArgParser(description: str, version_msg) -> ArgumentParser:
    """
    Setup command line argument parser

    Args:
        description(str): the description
        version_msg(str): the version message

    Returns:
        ArgumentParser: the argument parser
    """
    parser = ArgumentParser(
        description=description, formatter_class=RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-a",
        "--about",
        help="show about info [default: %(default)s]",
        action="store_true",
    )
    parser.add_argument(
        "-c",
        "--client",
        action="store_true",
        help="start client [default: %(default)s]",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="force update [default: %(default)s]",
    )
    parser.add_argument(
        "-d",
        "--debug",
        dest="debug",
        action="store_true",
        help="show debug info [default: %(default)s]",
    )
    parser.add_argument(
        "--host",
        default=JustpyServer.getDefaultHost(),
        help="the host to serve / listen from [default: %(default)s]",
    )
    parser.add_argument(
        "-l",
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
        "--port",
        type=int,
        default=9998,
        help="the port to serve from [default: %(default)s]",
    )
    parser.add_argument(
        "-s",
        "--serve",
        action="store_true",
        help="start webserver [default: %(default)s]",
    )
    parser.add_argument(
        "-nq",
        "--namedqueries",
        action="store_true",
        help="generate named queries [default: %(default)s]",
    )
    parser.add_argument("-V", "--version", action="version", version=version_msg)
    return parser


def main(argv=None):  # IGNORE:C0111
    """main program."""

    if argv is None:
        argv = sys.argv[1:]

    program_name = "ceur-ws"
    program_version = f"v{Version.version}"
    program_build_date = str(Version.date)
    program_version_message = f"{program_name} ({program_version},{program_build_date})"

    try:
        parser = getArgParser(
            description=Version.license, version_msg=program_version_message
        )
        args = parser.parse_args(argv)
        if len(argv) < 1:
            parser.print_usage()
            sys.exit(1)
        if args.about:
            print(program_version_message)
            print(f"see {Version.doc_url}")
            webbrowser.open(Version.doc_url)
        if args.serve:
            from ceurws.volumebrowser import VolumeBrowser

            volumeBrowser = VolumeBrowser(version=Version, args=args)
            volumeBrowser.start(host=args.host, port=args.port, debug=args.debug)
            pass
        if args.client:
            url = f"http://{args.host}:{args.port}"
            webbrowser.open(url)
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
            endpoint=wdsync.dbpEndpoint
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
            print (table)
            pass
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 1
    except Exception as e:
        if DEBUG:
            raise (e)
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        if args.debug:
            print(traceback.format_exc())
        return 2


DEBUG = 1
if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-d")
    sys.exit(main())
