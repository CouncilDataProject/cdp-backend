#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
from typing import Optional

import dask.dataframe as dd

###############################################################################


def get_content_type(uri: str) -> Optional[str]:
    # Media types retrieved from:
    # http://www.iana.org/assignments/media-types/media-types.xhtml
    content_types = dd.read_csv(
        str(Path(__file__).parent / "resources" / "content-types-*.csv")
    )

    # Get suffix from URI
    splits = uri.split(".")
    tail = splits[-1]

    # Find content type
    matching = content_types[content_types["Name"] == tail].compute()

    # If there is exactly one matching type, return it
    if len(matching) == 1:
        return matching["Template"].values[0]

    # Otherwise, return none
    return None
