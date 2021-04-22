#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
import logging
import sys
import traceback
from pathlib import Path

from gcsfs import GCSFileSystem

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
            prog="clean_cdp_filestore",
            description="Delete all files in a CDP filestore.",
        )
        p.add_argument(
            "google_credentials_file",
            type=Path,
            help="Path to Google service account JSON key.",
        )
        p.parse_args(namespace=self)


###############################################################################


def _clean_cdp_filestore(google_creds_path: Path) -> None:
    # Connect to database
    fs = GCSFileSystem(token=str(google_creds_path))

    # Open the key to get the project id
    with open(google_creds_path, "r") as open_resource:
        creds = json.load(open_resource)
        project_id = creds["project_id"]

    # Remove all files in bucket
    bucket = f"{project_id}.appspot.com"
    log.info(f"Cleaning bucket: {bucket}")
    try:
        fs.rm(f"{bucket}/*")
    # Handle empty bucket
    except FileNotFoundError:
        pass

    log.info("Filestore cleaning complete")


def main() -> None:
    try:
        args = Args()
        _clean_cdp_filestore(google_creds_path=args.google_credentials_file)
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
