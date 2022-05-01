#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import traceback
from pathlib import Path

from distributed import LocalCluster
from prefect import executors

from cdp_backend.pipeline import event_index_pipeline as pipeline
from cdp_backend.pipeline.pipeline_config import EventIndexPipelineConfig

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
            prog="run_cdp_event_index",
            description=(
                "Index all event (session) transcripts from a CDP infrastructure."
            ),
        )
        p.add_argument(
            "config_file",
            type=Path,
            help=(
                "Path to the pipeline configuration file. "
                "See cdp_backend.pipeline.pipeline_config.EventIndexPipelineConfig "
                "for more details."
            ),
        )
        p.add_argument(
            "-n",
            "--n_grams",
            type=int,
            default=1,
            help="N number of terms to act as a unique entity.",
        )
        p.add_argument(
            "-l",
            "--store_local",
            action="store_true",
            help=(
                "Should the pipeline store the generated index to a local parquet file."
            ),
        )
        p.add_argument(
            "-p",
            "--parallel",
            action="store_true",
            dest="parallel",
            help=(
                "Boolean option to spin up a local multi-threaded "
                "Dask Distributed cluster for event processing."
            ),
        )

        p.parse_args(namespace=self)


def main() -> None:
    try:
        args = Args()
        with open(args.config_file, "r") as open_resource:
            config = EventIndexPipelineConfig.from_json(  # type: ignore
                open_resource.read()
            )

        # Get flow definition
        flow = pipeline.create_event_index_pipeline(
            config=config,
            n_grams=args.n_grams,
            store_local=args.store_local,
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
            state = flow.run(
                executor=executors.DaskExecutor(address=distributed_executor_address),
            )

            # Shutdown cluster after run
            cluster.close()

        else:
            state = flow.run()

        if state.is_failed():
            raise ValueError("Flow run failed.")

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
