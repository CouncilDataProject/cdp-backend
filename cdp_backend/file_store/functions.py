#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from pathlib import Path
from typing import Optional

from fsspec.implementations.local import LocalFileSystem
from gcsfs import GCSFileSystem

###############################################################################

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)4s: %(module)s:%(lineno)4s %(asctime)s] %(message)s",
)
log = logging.getLogger(__name__)

GCS_URI = "gs://{bucket}/{filename}"

###############################################################################


def initialize_gcs_file_system(credentials_file: str) -> GCSFileSystem:
    return GCSFileSystem(token=credentials_file)


def get_file_uri(bucket: str, filename: str, creds_file: str) -> Optional[str]:
    fs = initialize_gcs_file_system(creds_file)

    if fs.exists(f"{bucket}/{filename}"):
        return GCS_URI.format(bucket=bucket, filename=filename)

    return None


def upload_file(
    fs: GCSFileSystem,
    bucket: str,
    filepath: str,
    save_name: Optional[str] = None,
    remove_local: bool = False,
) -> str:

    # Resolve the path to enforce path complete
    filepath = Path(filepath).resolve(strict=True)

    # Create save name if none provided
    if not save_name:
        save_name = filepath.name

    # Try to get the file first
    uri = get_file_uri(fs, bucket, save_name)

    # Return existing uri and remove local copy if desired
    if uri:
        if remove_local:
            remove_local_file(filepath)

        return uri

    # If no existing file, upload and remove local copy if desired
    else:
        save_url = GCS_URI.format(bucket=bucket, filename=save_name)

        fs.put_file(filepath, f"{bucket}/{save_name}")

        if remove_local:
            remove_local_file(filepath)

        return save_url


def remove_local_file(filepath: str) -> None:
    fs = LocalFileSystem()
    fs.rm(filepath)

    log.info(f"Removed {filepath} from local file system.")
