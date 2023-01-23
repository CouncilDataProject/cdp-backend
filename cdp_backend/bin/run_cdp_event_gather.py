#!/usr/bin/env python

import argparse
import logging
import sys
import traceback
from pathlib import Path

from cdp_backend.pipeline import event_gather_pipeline as pipeline
from cdp_backend.pipeline.pipeline_config import EventGatherPipelineConfig

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
            "config_file",
            type=Path,
            help=(
                "Path to the pipeline configuration file. "
                "See cdp_backend.pipeline.pipeline_config.EventGatherPipelineConfig "
                "for more details."
            ),
        )
        p.add_argument(
            "-f",
            "--from",
            type=str,
            default=None,
            help=(
                "Optional ISO formatted string to pass to the get_event function to act"
                "as the start point for event gathering."
            ),
            dest="from_dt",
        )
        p.add_argument(
            "-t",
            "--to",
            type=str,
            default=None,
            help=(
                "Optional ISO formatted string to pass to the get_event function to act"
                "as the end point for event gathering."
            ),
            dest="to_dt",
        )

        p.parse_args(namespace=self)


def main() -> None:
    try:
        args = Args()
        with open(args.config_file) as open_resource:
            config = EventGatherPipelineConfig.from_json(open_resource.read())

        # Get flow definition
        flow = pipeline.create_event_gather_flow(
            config=config,
            from_dt=args.from_dt,
            to_dt=args.to_dt,
        )

        # Run pipeline
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
