#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
import logging
import sys
import traceback
from importlib import import_module
from pathlib import Path
from typing import Callable

from distributed import LocalCluster
from prefect import executors

from cdp_backend.pipeline import event_gather_pipeline as pipeline

###############################################################################

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)4s: %(module)s:%(lineno)4s %(asctime)s] %(message)s",
)
log = logging.getLogger(__name__)

###############################################################################


class Args(argparse.Namespace):
    def __init__(self) -> None:
        self.__parse()

    def __parse(self) -> None:
        p = argparse.ArgumentParser(
            prog="run_cdp_event_gather",
            description="Gather, process, and store event data to CDP infrastructure.",
        )
        p.add_argument(
            "-g",
            "--google-credentials-file",
            default=(Path(__file__).parent.parent.parent / "cdp-creds.json"),
            type=Path,
            dest="google_credentials_file",
            help="Path to the Google Service Account Credentials JSON file.",
        )
        p.add_argument(
            "-e",
            "--get_events_function_path",
            type=Path,
            dest="get_events_function_path",
            help=(
                "Path to the function (including function name) that "
                "supplies event data to the CDP event gather pipeline."
            ),
        )
        p.add_argument(
            "-b",
            "--google_cloud_storage_bucket_name",
            type=Path,
            dest="gcs_bucket",
            help=(
                "Google Cloud Storage bucket name for file uploads. "
                "Default: None (assume bucket name from GCP project id)"
            ),
        )
        p.add_argument(
            "--p",
            "--parallel",
            action="store_true",
            dest="parallel",
            help=(
                "Boolean option to spin up a local multi-threaded "
                "Dask Distributed cluster for event processing."
            ),
        )

        p.parse_args(namespace=self)


def import_get_events_func(func_path: Path) -> Callable:
    path, func_name = str(func_path).rsplit(".", 1)
    mod = import_module(path)

    return getattr(mod, func_name)


def main() -> None:
    try:
        args = Args()

        # Unpack args
        credentials_file = args.google_credentials_file
        get_events_func = import_get_events_func(args.get_events_function_path)

        # Handle default None bucket
        if args.gcs_bucket is None:
            with open(credentials_file, "r") as open_resource:
                project_id = json.load(open_resource)["project_id"]
                bucket = f"{project_id}.appspot.com"
                log.info(f"Defaulting to bucket: {bucket}")
        else:
            bucket = args.gcs_bucket

        # Get flow definition
        flow = pipeline.create_event_gather_flow(
            get_events_func, credentials_file, bucket
        )

        # Determine executor
        if args.parallel:
            # Create local cluster
            log.info("Creating LocalCluster")
            cluster = LocalCluster(processes=False)
            log.info("Created LocalCluster")

            # Set distributed_executor_address
            distributed_executor_address = cluster.scheduler_address

            # Log dashboard URI
            log.info(f"Dask dashboard available at: {cluster.dashboard_link}")

            # Use dask cluster
            flow.run(
                executor=executors.DaskExecutor(address=distributed_executor_address),
            )

        else:
            flow.run()

    except Exception as e:
        log.error("=============================================")
        log.error("\n\n" + traceback.format_exc())
        log.error("=============================================")
        log.error("\n\n" + str(e) + "\n")
        log.error("=============================================")
        sys.exit(1)


###############################################################################
# Allow caller to directly run this module (usually in development scenarios)

if __name__ == "__main__":
    main()
