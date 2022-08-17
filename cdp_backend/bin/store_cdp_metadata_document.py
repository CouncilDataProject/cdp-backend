#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import traceback
from pathlib import Path

import yaml
from google.cloud.firestore import Client

from .. import __version__

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
            prog="store_cdp_metadata_document",
            description="Store the CDP metadata document to a firestore instance.",
        )
        p.add_argument(
            "cookiecutter_yaml",
            type=Path,
            help="Path to the CDP Cookiecutter YAML file to lookup metadata details.",
        )
        p.parse_args(namespace=self)


###############################################################################


def _store_cdp_metadata_document(
    cookiecutter_yaml: Path,
) -> None:
    # Read the cookiecutter file
    with open(cookiecutter_yaml, "r") as open_f:
        cookiecutter_meta = yaml.load(open_f, Loader=yaml.FullLoader)["default_context"]

    # Open client and write doc
    client = Client()
    collection = client.collection("metadata")
    collection.document("configuration").set(
        {
            "infrastructure_version": __version__,
            "municipality_name": cookiecutter_meta["municipality"],
            "hosting_github_url": cookiecutter_meta["hosting_github_url"],
            "hosting_web_app_address": cookiecutter_meta["hosting_web_app_address"],
            "firestore_location": cookiecutter_meta["firestore_region"],
            "governing_body": cookiecutter_meta["governing_body_type"],
        }
    )


def main() -> None:
    try:
        args = Args()
        _store_cdp_metadata_document(
            cookiecutter_yaml=args.cookiecutter_yaml,
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
