#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import traceback
from pathlib import Path

import fireo

from cdp_backend.database import DATABASE_MODELS

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
            prog="clean_cdp_database",
            description="Delete all collections in a CDP database.",
        )
        p.add_argument(
            "google_credentials_file",
            type=Path,
            help="Path to Google service account JSON key.",
        )
        p.parse_args(namespace=self)


###############################################################################


def _clean_cdp_database(google_creds_path: Path) -> None:
    # Connect to database
    fireo.connection(from_file=google_creds_path)

    # Iter through database models and delete the whole collection
    for model in DATABASE_MODELS:
        log.info(f"Cleaning collection: {model.collection_name}")
        model.collection.delete()

    log.info("Database cleaning complete")


def main() -> None:
    try:
        args = Args()
        _clean_cdp_database(google_creds_path=args.google_credentials_file)
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
