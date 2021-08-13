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

