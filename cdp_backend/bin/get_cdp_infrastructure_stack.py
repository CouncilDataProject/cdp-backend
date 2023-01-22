#!/usr/bin/env python

import argparse
import json
import logging
import shutil
import sys
import traceback
from pathlib import Path

from cdp_backend.database import DATABASE_MODELS
from cdp_backend.infrastructure import INFRA_DIR

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
            prog="get_cdp_infrastructure_stack",
            description=(
                "Generate or copy all the files needed for a new CDP infrastructure."
            ),
        )
        p.add_argument(
            "output_dir",
            type=Path,
            help=(
                "Path to where the infrastructure files should be copied "
                "or generated."
            ),
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


def _copy_infra_files(output_dir: Path) -> None:
    # Copy each file in the infra dir to the output dir
    output_dir.mkdir(parents=True, exist_ok=True)
    for f in INFRA_DIR.iterdir():
        if f.name not in [
            "__pycache__",
            "__init__.py",
        ]:
            out_ = output_dir / f.name
            if f.is_file():
                shutil.copy(f, out_)
                log.info(f"Copied {f.name} to {output_dir}")
            elif f.is_dir():
                if out_.exists():
                    shutil.rmtree(out_)
                shutil.copytree(f, out_)
                log.info(f"Copied {f.name} to {output_dir}")
            else:
                raise TypeError(
                    f"When copying files, encountered object that "
                    f"isn't a file or directory: '{f}'"
                )


def main() -> None:
    try:
        args = Args()
        output_dir = args.output_dir.expanduser().resolve()
        _copy_infra_files(output_dir=output_dir)
        _generate_indexes_json(outfile=output_dir / "firestore.indexes.json")
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
