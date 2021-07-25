#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import traceback
from pathlib import Path

from cdp_backend.pipeline import event_gather_pipeline as pipeline
from cdp_backend.pipeline.mock_get_events import (
    FILLED_FLOW_CONFIG,
    MANY_FLOW_CONFIG,
    MINIMAL_FLOW_CONFIG,
)

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
            prog="cdp_event_gather",
            description="Gather, process, and store event data to CDP infrastructure.",
        )
        p.add_argument(
            "-o",
            "--output-file-spec",
            type=Path,
            default=Path("cdp_event_gather_flow_{ftype}.png"),
            dest="output_file",
            help=(
                "Path spec to where to store the created PNG files. "
                "Use `{ftype}` as the formatted spec parameter."
            ),
        )
        p.parse_args(namespace=self)


def main() -> None:
    try:
        args = Args()

        # Minimum event flow
        minimal_flow = pipeline.create_event_gather_flow(MINIMAL_FLOW_CONFIG)
        minimal_flow.visualize(
            filename=str(args.output_file.with_suffix("")).format(ftype="minimal"),
            format="png",
        )

        # Filled event flow
        filled_flow = pipeline.create_event_gather_flow(FILLED_FLOW_CONFIG)
        filled_flow.visualize(
            filename=str(args.output_file.with_suffix("")).format(ftype="filled"),
            format="png",
        )

        # Many events flow
        many_flow = pipeline.create_event_gather_flow(MANY_FLOW_CONFIG)
        many_flow.visualize(
            filename=str(args.output_file.with_suffix("")).format(ftype="many"),
            format="png",
        )

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
