#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import traceback

from importlib import import_module
from pathlib import Path
from typing import Callable

import cdp_backend.pipeline.cdp_event_gather_pipeline as pipeline

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
            "-g",
            "--google-credentials-file",
            default=(
                Path(__file__).parent.parent.parent
                / "stg-cdp-seattle-a910f-45df66e72d75.json"
            ),
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
        p.parse_args(namespace=self)


def import_get_events_func(func_path: Path) -> Callable:
    path, func_name = str(func_path).rsplit(".", 1)
    mod = import_module(path)

    return getattr(mod, func_name)


def main() -> None:
    try:
        args = Args()

        credentials_file = args.google_credentials_file

        get_events_func = import_get_events_func(args.get_events_function_path)

        flow = pipeline.create_cdp_event_gather_flow(get_events_func, credentials_file)

        # TODO make the flow run on a certain type of Executor?
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
