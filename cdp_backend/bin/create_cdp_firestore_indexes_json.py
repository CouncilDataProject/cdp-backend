#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
import logging
import sys
import traceback
from pathlib import Path

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
            prog="create_cdp_firestore_indexes_json",
            description="Create the CDP Firestore indexes JSON file.",
        )
        p.add_argument(
            "outfile",
            type=Path,
            help="Path to where the indexes JSON file should be stored.",
        )
        p.parse_args(namespace=self)


###############################################################################


def _generate_indexes_json(outfile: Path) -> None:
    # All indexes
    indexes = []

    for model_cls in DATABASE_MODELS:
        for idx_field_set in model_cls._INDEXES:

            indexes.append(
                {
                    "collectionGroup": model_cls.collection_name,
                    "queryScope": "COLLECTION",
                    "fields": idx_field_set.to_dict()["fields"],
                }
            )

    # Add indexes to the normal JSON format
    indexes_full_json = {
        "indexes": indexes,
        "fieldOverrides": [],
    }

    # Write out the file
    outfile = outfile.resolve()
    with open(outfile, "w") as open_f:
        json.dump(indexes_full_json, open_f, indent=2)
    log.info(f"Wrote out CDP firestore.indexes.json to: '{outfile}'")


def main() -> None:
    try:
        args = Args()
        _generate_indexes_json(outfile=args.outfile)
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
