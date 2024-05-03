"""
Script to download and install entity fishing docker instance with datasets

Created on 2024-04-25

@author: tholzheim
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def get_datasets() -> list[str]:
    """
    Get all entity fishing datasets
    """
    datasets = [
        "https://science-miner.s3.amazonaws.com/entity-fishing/0.0.6/db-kb.zip",
        "https://science-miner.s3.amazonaws.com/entity-fishing/0.0.6/db-en.zip",
        "https://science-miner.s3.amazonaws.com/entity-fishing/0.0.6/db-fr.zip",
        "https://science-miner.s3.amazonaws.com/entity-fishing/0.0.6/db-de.zip",
        "https://science-miner.s3.amazonaws.com/entity-fishing/0.0.6/db-es.zip",
        "https://science-miner.s3.amazonaws.com/entity-fishing/0.0.6/db-it.zip",
        "https://science-miner.s3.amazonaws.com/entity-fishing/0.0.6/db-ar.zip",
        "https://science-miner.s3.amazonaws.com/entity-fishing/0.0.6/db-zh.zip",
        "https://science-miner.s3.amazonaws.com/entity-fishing/0.0.6/db-ru.zip",
        "https://science-miner.s3.amazonaws.com/entity-fishing/0.0.6/db-ja.zip",
        "https://science-miner.s3.amazonaws.com/entity-fishing/0.0.6/db-pt.zip",
        "https://science-miner.s3.amazonaws.com/entity-fishing/0.0.6/db-fa.zip",
        "https://science-miner.s3.amazonaws.com/entity-fishing/0.0.6/db-uk.zip",
        "https://science-miner.s3.amazonaws.com/entity-fishing/0.0.6/db-sv.zip",
        "https://science-miner.s3.amazonaws.com/entity-fishing/0.0.6/db-bn.zip",
        "https://science-miner.s3.amazonaws.com/entity-fishing/0.0.6/db-hi.zip",
    ]
    return datasets


def base_directory() -> Path:
    """
    Get default storage entity fishing related content
    """
    return Path.home().joinpath(".ceurws", "entity-fishing")


def data_directory() -> Path:
    """
    Get default location to store the datasets
    """
    return base_directory().joinpath("data", "db")


def config_directory() -> Path:
    """
    Get the default location for configuration files
    """
    return base_directory().joinpath("config")


def directory_size(directory: Path) -> Optional[int]:
    """
    Calculate directory size
    """
    size = None
    if directory.is_dir():
        size = sum(f.stat().st_size for f in directory.glob("**/*") if f.is_file())
    return size


def unzip_file(zip_file: Path):
    """
    unzip give file
    """
    logger.info(f"Start unzipping {zip_file}")
    try:
        subprocess.run(["unzip", "-q", zip_file, "-d", zip_file.parent], check=True)
        logger.info(f"Successfully unzipped  {zip_file.name}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error unzipping {zip_file}")
        logger.debug(e)


def download(url: str, target_path: Path) -> bool:
    """
    download given url and store the file at the given target location
    """
    logger.info(f"Start downloading {url}")
    downloaded = False
    try:
        subprocess.run(["wget", "-qO", str(target_path), str(url)], check=True)
        logger.info(f"Successfully downloaded  {Path(url).name}")
        downloaded = True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error downloading {url}")
        logger.debug(e)
    return downloaded


def download_datasets(urls: list[str]):
    """
    check if the given list of datasets exists and download if missing
    """
    target_dir = data_directory()
    target_dir.mkdir(parents=True, exist_ok=True)
    for url in urls:
        zip_file = target_dir.joinpath(Path(url).name)
        unzipped_dir = target_dir.joinpath(Path(url).stem)
        if unzipped_dir.exists() and directory_size(unzipped_dir) > 0:
            # dataset already exists and in unzipped
            logger.info(f"Dataset {unzipped_dir.name} already exists ({directory_size(unzipped_dir)/1e9:.02f} GB)")
            pass
        elif zip_file.exists() and zip_file.is_file():
            # dataset is downloaded but not unzipped
            logger.info(f"Dataset {zip_file.name} already downloaded ({zip_file.stat().st_size/1e9:.02f})")
            unzip_file(zip_file)
        else:
            # dataset needs to be downloaded
            logger.info(f"Dataset {Path(url).name} missing")
            has_downloaded = download(url, zip_file)
            if has_downloaded:
                if zip_file.exists():
                    unzip_file(zip_file)
                else:
                    logger.warning(f"{url} downloaded but zip file is missing")


def docker_container_name() -> str:
    """
    Get the default entity_fishing container name
    """
    return "pyceurmake-entity-fishing-instance"


def stop_docker_container(container_name: str):
    """
    stop the docker container
    """
    try:
        logger.info(f"Stopping docker container {container_name}")
        subprocess.run(["docker", "stop", container_name], check=True, stdout=subprocess.PIPE)
        logger.info(f"Stopped docker container {container_name}")
    except subprocess.CalledProcessError:
        logger.info(f"Docker container {container_name} could not be stopped. (container was probably not running)")


def remove_docker_container(container_name: str):
    """
    remove the docker container
    """
    try:
        logger.info(f"Removing docker container {container_name}")
        subprocess.run(["docker", "rm", container_name], check=True)
        logger.info(f"Docker container {container_name} removed")
    except subprocess.CalledProcessError:
        logger.info(f"Docker container {container_name} could not be removed. (container was probably already deleted)")


def start_docker_container(
    container_name: str,
    datasets: list[str],
    console_port: int = 8090,
    service_port: int = 8091,
    detached: bool = True,
    use_config: bool = False,
):
    """
    start the entity-fishing docker container and map the dataset volumes

    Example command
        docker run --rm --name pyceurmake-entity-fishing-instance \
          -p 8090:8090 -p 8091:8091 \
          -v $HOME/.ceurws/entity-fishing/data/db/db-kb:/opt/entity-fishing/data/db/db-kb \
          -v $HOME/.ceurws/entity-fishing/data/db/db-en:/opt/entity-fishing/data/db/db-en \
          grobid/entity-fishing:0.0.6
    """

    cmd = ["docker", "run", "--rm"]
    if detached:
        cmd.append("-d")
    cmd.extend(["--name", container_name])
    cmd.extend(["-p", f"{console_port}:8090", "-p", f"{service_port}:8091"])
    storage_path = data_directory()
    for dataset in datasets:
        name = Path(dataset).stem
        volume_map = f"{storage_path}/{name}:/opt/entity-fishing/data/db/{name}"
        cmd.extend(["-v", volume_map])
    if use_config:
        config_files = ["kb.yaml"]
        config_dir = config_directory()
        for config_file in config_files:
            config_path = config_dir.joinpath(config_file)
            if config_path.exists():
                logger.info(f"Using config file {config_path}")
                config_map = f"{config_path}:/opt/entity-fishing/data/config/{config_file}"
                cmd.extend(["-v", config_map])
            else:
                logger.info(f"Config file {config_path} not found. Default version of {config_file} will be used")
    cmd.extend(["grobid/entity-fishing:0.0.6"])
    try:
        logger.info("Starting docker container")
        logger.debug(f"Executing ${cmd}")
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error("Unable to start the docker container")
        logger.debug(e)


def main(argv=None):
    """
    main routine
    """

    if argv is None:
        argv = sys.argv

    def download_cmd(args: argparse.Namespace):
        """
        handle the download cmd and args
        """
        datasets = get_datasets()
        download_datasets(datasets)

    def docker_start_cmd(args: argparse.Namespace):
        """
        handle start of the docker container
        """
        container_name = args.container_name
        console_port = args.console_port
        service_port = args.service_port
        detached = not args.attached
        use_config = args.use_config
        datasets = get_datasets()
        stop_docker_container(container_name)
        start_docker_container(
            container_name=container_name,
            datasets=datasets,
            console_port=console_port,
            service_port=service_port,
            detached=detached,
            use_config=use_config,
        )

    def docker_stop_cmd(args: argparse.Namespace):
        """
        handle stop of the docker container
        """
        container_name = args.container_name
        stop_docker_container(container_name)

    parser = argparse.ArgumentParser(prog="PROG")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--debug", dest="debug", action="store_true", help="enable debug log output")
    subparsers = parser.add_subparsers(help="sub-command help")
    # handle dataset downloads
    parser_download = subparsers.add_parser("download", help="download entity-fishing datasets", parents=[common])
    parser_download.set_defaults(func=download_cmd)
    # handle docker start
    parser_docker_start = subparsers.add_parser(
        "container-start", help="start entity-fishing docker container", parents=[common]
    )
    parser_docker_start.set_defaults(func=docker_start_cmd)
    parser_docker_start.add_argument(
        "-n",
        "--container-name",
        dest="container_name",
        help="name of the docker container",
        default=docker_container_name(),
    )
    parser_docker_start.add_argument("--console-port", dest="console_port", help="console port", default=8090)
    parser_docker_start.add_argument("--service-port", dest="service_port", help="service port", default=8091)
    parser_docker_start.add_argument(
        "-a", "--attached", dest="attached", help="start the container attached to the console", action="store_true"
    )
    parser_docker_start.add_argument(
        "-c",
        "--config",
        dest="use_config",
        help=f"use the provided config files from {config_directory()}",
        action="store_true",
    )
    # handle docker stop
    parser_docker_stop = subparsers.add_parser(
        "container-stop", help="stop entity-fishing docker container", parents=[common]
    )
    parser_docker_stop.set_defaults(func=docker_stop_cmd)
    parser_docker_stop.add_argument(
        "-n",
        "--container-name",
        dest="container_name",
        help="name of the docker container",
        default=docker_container_name(),
    )

    args = parser.parse_args(argv[1:])
    # configure logger
    log_format = "[%(asctime)s] [%(levelname)s] %(message)s"
    level = logging.INFO
    if args.debug:
        level = logging.DEBUG
    logging.basicConfig(format=log_format, datefmt="%Y-%m-%d %H:%M:%S", level=level)
    # handle cmd
    args.func(args)


if __name__ == "__main__":
    main()
