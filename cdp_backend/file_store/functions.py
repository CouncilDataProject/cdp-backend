#!/usr/bin/env python

from __future__ import annotations

import logging
from pathlib import Path

from fsspec.implementations.local import LocalFileSystem
from gcsfs import GCSFileSystem

###############################################################################

log = logging.getLogger(__name__)

GCS_URI = "gs://{bucket}/{filename}"

###############################################################################


def initialize_gcs_file_system(credentials_file: str) -> GCSFileSystem:
    """
    Initializes an instance of a GCSFileSystem.

    Parameters
    ----------
    credentials_file: str
        The path to the Google Service Account credentials JSON file.

    Returns
    -------
    file_system: GCSFileSystem
        An initialized GCSFileSystem.
    """
    return GCSFileSystem(token=str(credentials_file))


def get_file_uri(bucket: str, filename: str, credentials_file: str) -> str | None:
    """
    Gets the file uri of a filename and bucket for a given Google Cloud file store.

    Parameters
    ----------
    bucket: str
        The bucket name to check for the file.
    filename: str
        The filename of the file to check for.
    credentials_file: str
        The path to the Google Service Account credentials JSON file used
        to initialize the file store connection.

    Returns
    -------
    file_uri: Optional[str]
        The file uri if the file exists, otherwise returns None.
    """
    fs = initialize_gcs_file_system(credentials_file)

    if fs.exists(f"{bucket}/{filename}"):
        return GCS_URI.format(bucket=bucket, filename=filename)

    return None


def upload_file(
    credentials_file: str,
    bucket: str,
    filepath: str,
    save_name: str | None = None,
    remove_local: bool = False,
    overwrite: bool = False,
) -> str:
    """
    Uploads a file to a Google Cloud file store bucket.
    If save_name is provided, that will be used as the file's save name
    instead of the file's local name.
    If remove_local is provided, the local file will be removed upon
    successful upload.

    Parameters
    ----------
    credentials_file: str
        The path to the Google Service Account credentials JSON file used
        to initialize the file store connection.
    bucket: str
        The name of the file store bucket to upload to.
    filepath: str
        The filepath to the local file to upload.
    save_name: Optional[str]
        The name to save the file as in the file store.
    remove_local: bool
        If True, remove the local file upon successful upload.
    overwrite: bool
        Boolean value indicating whether or not to overwrite the remote resource with
        the same name if it already exists.

    Returns
    -------
    uri: str
        The uri of the uploaded file in the file store.
    """
    fs = initialize_gcs_file_system(credentials_file)

    # Resolve the path to enforce path complete
    resolved_filepath = Path(filepath).resolve(strict=True)

    # Create save name if none provided
    if not save_name:
        save_name = resolved_filepath.name

    # Try to get the file first
    uri = get_file_uri(bucket, save_name, credentials_file)

    # Return existing uri and remove local copy if desired
    if uri and not overwrite:
        if remove_local:
            remove_local_file(resolved_filepath)

        return uri

    # If no existing file, upload and remove local copy if desired
    else:
        save_url = GCS_URI.format(bucket=bucket, filename=save_name)
        remote_uri = f"{bucket}/{save_name}"
        fs.put_file(resolved_filepath, remote_uri)

        if remove_local:
            remove_local_file(resolved_filepath)

        log.info(f"Uploaded local file: {resolved_filepath} to {remote_uri}")
        return save_url


def download_file(
    credentials_file: str,
    bucket: str,
    remote_filepath: str,
    save_path: str,
) -> str:
    fs = initialize_gcs_file_system(credentials_file)
    fs.get(f"{bucket}/{remote_filepath}", save_path)
    return save_path


def get_open_url_for_gcs_file(credentials_file: str, uri: str) -> str:
    """
    Simple wrapper around fsspec.FileSystem.url function for creating a connection
    to the filesystem then getting the hosted / web accessible URL to the file.

    Parameters
    ----------
    credentials_file: str
        The path to the Google Service Account credentials JSON file used
        to initialize the file store connection.
    uri: str
        The URI to the file already stored to get a web accessible URL for.

    Returns
    -------
    url: str
        The web accessible URL for the file.
    """
    fs = initialize_gcs_file_system(credentials_file=credentials_file)
    return str(fs.url(uri))


def remove_local_file(filepath: str | Path) -> None:
    """
    Deletes a file from the local file system.

    Parameters
    ----------
    filepath: str
        The filepath of the local file to delete.
    """
    fs = LocalFileSystem()
    fs.rm(str(filepath))

    log.debug(f"Removed {filepath} from local file system.")


def upload_file_and_return_link(
    credentials_file: str,
    bucket: str,
    filepath: str,
    save_name: str | None = None,
    remove_local: bool = False,
) -> str:
    """
    Parameters
    ----------
    credentials_file: str
        The path to the Google Service Account credentials JSON file used
        to initialize the file store connection.
    bucket: str
        The name of the file store bucket to upload to.
    filepath: str
        The filepath to the local file to upload.
    save_name: Optional[str]
        The name to save the file as in the file store.
    remove_local: bool
        If True, remove the local file upon successful upload.

    Returns
    -------
    str
        HTTPS link to the uploaded file.
    """
    # Bucket doesn't need gs://
    # It actually fails if it is included
    if bucket.startswith("gs://"):
        bucket = bucket.replace("gs://", "")

    # Upload
    uri = upload_file(
        credentials_file=credentials_file,
        bucket=bucket,
        filepath=filepath,
        save_name=save_name,
        remove_local=remove_local,
    )

    # Return link (lasts until file deletion)
    return get_open_url_for_gcs_file(credentials_file=credentials_file, uri=uri)
