#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import traceback
from pathlib import Path

from distributed import LocalCluster
from prefect import executors

from cdp_backend.pipeline import process_event_index_chunk_pipeline as pipeline
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
            prog="process_cdp_event_index_chunk",
            description=(
                "Download a single event index chunk from remote storage, "
                "then process it and upload ngrams to a CDP database."
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
            "chunk",
            type=Path,
            help="Filename for the parquet index chunk to process and upload.",
        )
        p.add_argument(
            "--upload_batch_size",
            type=int,
            default=500,
            help="Number of ngrams to upload to database in a single batch.",
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
            config = EventIndexPipelineConfig.from_json(open_resource.read())

        # Get flow definition
        flow = pipeline.create_event_index_upload_pipeline(
            config=config,
            index_chunk=args.chunk,
            upload_batch_size=args.upload_batch_size,
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
