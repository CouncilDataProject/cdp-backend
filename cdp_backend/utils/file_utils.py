#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import shutil
from pathlib import Path
from typing import Optional, Union

import dask.dataframe as dd
import requests

###############################################################################

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)4s: %(module)s:%(lineno)4s %(asctime)s] %(message)s",
)
log = logging.getLogger(__name__)

###############################################################################


def get_media_type(uri: str) -> Optional[str]:
    """
    Get the IANA media type for the provided URI.
    If one could not be found, return None.

    Parameters
    ----------
    uri: str
        The URI to get the IANA media type for.

    Returns
    -------
    mtype: Optional[str]:
        The found matching IANA media type.
    """
    # Media types retrieved from:
    # http://www.iana.org/assignments/media-types/media-types.xhtml
    media_types = dd.read_csv(
        str(Path(__file__).parent / "resources" / "content-types-*.csv")
    )

    # Get suffix from URI
    splits = uri.split(".")
    suffix = splits[-1]

    # Find content type
    matching = media_types[media_types["Name"] == suffix].compute()

    # If there is exactly one matching type, return it
    if len(matching) == 1:
        return matching["Template"].values[0]

    # Otherwise, return none
    return None


def external_resource_copy(
    uri: str, dst: Optional[Union[str, Path]] = None, overwrite: bool = False
) -> str:
    """
    Copy an external resource to a local destination on the machine.
    Parameters
    ----------
    uri: str
        The uri for the external resource to copy.
    dst: Optional[Union[str, Path]]
        A specific destination to where the copy should be placed. If None provided
        stores the resource in the current working directory.
    overwrite: bool
        Boolean value indicating whether or not to overwrite a local resource with
        the same name if it already exists.
    Returns
    -------
    saved_path: str 
        The path of where the resource ended up getting copied to.
    """
    if dst is None:
        dst = uri.split("/")[-1]

    # Ensure dst doesn't exist
    dst = Path(dst).resolve()
    if dst.is_dir():
        dst = dst / uri.split("/")[-1]
    if dst.is_file() and not overwrite:
        raise FileExistsError(dst)

    # Open requests connection to uri as a stream
    log.debug(f"Beginning external resource copy from: {uri}")
    with requests.get(uri, stream=True) as streamed_read:
        streamed_read.raise_for_status()
        with open(dst, "wb") as streamed_write:
            shutil.copyfileobj(streamed_read.raw, streamed_write)
    log.debug(f"Completed external resource copy from: {uri}")
    log.info(f"Stored external resource copy: {dst}")

    return str(dst)
