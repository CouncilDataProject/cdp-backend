#!/usr/bin/env python

from __future__ import annotations

import os.path
from unittest import mock

import pytest
from gcsfs import GCSFileSystem

from cdp_backend.file_store import functions

###############################################################################

FILENAME = "file.txt"
BUCKET = "bucket"
FILEPATH = "fake/path/" + FILENAME
SAVE_NAME = "fakeSaveName"
EXISTING_FILE_URI = "gs://bucket/" + SAVE_NAME
GCS_FILE_URI = functions.GCS_URI.format(bucket=BUCKET, filename=FILENAME)

###############################################################################


def test_initialize_gcs_file_system() -> None:
    with mock.patch("gcsfs.credentials.GoogleCredentials.connect"):
        assert isinstance(
            functions.initialize_gcs_file_system("path/to/credentials"), GCSFileSystem
        )


@pytest.mark.parametrize(
    "filename, bucket, exists, expected",
    [
        (
            FILENAME,
            BUCKET,
            True,
            functions.GCS_URI.format(bucket=BUCKET, filename=FILENAME),
        ),
        (FILENAME, BUCKET, False, None),
    ],
)
def test_get_file_uri(
    filename: str,
    bucket: str,
    exists: bool,
    expected: str | None,
) -> None:
    with mock.patch("gcsfs.credentials.GoogleCredentials.connect"):
        with mock.patch("gcsfs.GCSFileSystem.exists") as mock_exists:
            mock_exists.return_value = exists

            assert expected == functions.get_file_uri(bucket, filename, "path/to/creds")


@pytest.mark.parametrize(
    "bucket, filepath, save_name, remove_local, overwrite, existing_file_uri, expected",
    [
        (
            BUCKET,
            FILEPATH,
            SAVE_NAME,
            True,
            True,
            EXISTING_FILE_URI,
            EXISTING_FILE_URI,
        ),
        (
            BUCKET,
            FILEPATH,
            SAVE_NAME,
            True,
            True,
            None,
            EXISTING_FILE_URI,
        ),
        (
            BUCKET,
            FILEPATH,
            SAVE_NAME,
            True,
            False,
            EXISTING_FILE_URI,
            EXISTING_FILE_URI,
        ),
        (
            BUCKET,
            FILEPATH,
            SAVE_NAME,
            False,
            True,
            EXISTING_FILE_URI,
            EXISTING_FILE_URI,
        ),
        (
            BUCKET,
            FILEPATH,
            SAVE_NAME,
            False,
            True,
            None,
            EXISTING_FILE_URI,
        ),
        (
            BUCKET,
            FILEPATH,
            SAVE_NAME,
            False,
            False,
            EXISTING_FILE_URI,
            EXISTING_FILE_URI,
        ),
        (BUCKET, FILEPATH, None, False, True, GCS_FILE_URI, GCS_FILE_URI),
        (BUCKET, FILEPATH, None, False, True, None, GCS_FILE_URI),
        (BUCKET, FILEPATH, None, False, False, None, GCS_FILE_URI),
        (BUCKET, FILEPATH, None, True, True, GCS_FILE_URI, GCS_FILE_URI),
        (BUCKET, FILEPATH, None, True, True, None, GCS_FILE_URI),
        (BUCKET, FILEPATH, None, True, False, None, GCS_FILE_URI),
    ],
)
def test_upload_file(
    bucket: str,
    filepath: str,
    save_name: str | None,
    remove_local: bool,
    overwrite: bool,
    existing_file_uri: str,
    expected: str,
) -> None:
    with mock.patch("cdp_backend.file_store.functions.initialize_gcs_file_system"):
        with mock.patch(
            "cdp_backend.file_store.functions.get_file_uri"
        ) as mock_file_uri:
            with mock.patch("cdp_backend.file_store.functions.remove_local_file"):
                with mock.patch("pathlib.Path.resolve") as mock_path:
                    mock_file_uri.return_value = existing_file_uri
                    mock_path.return_value.name = FILENAME

                    assert expected == functions.upload_file(
                        "path/to/creds",
                        bucket,
                        filepath,
                        save_name,
                        remove_local,
                        overwrite,
                    )


# Type ignore because changing tmpdir typing
def test_remove_local_file(tmpdir) -> None:  # type: ignore
    print(type(tmpdir))
    p = tmpdir.mkdir("sub").join("hello.txt")
    p.write("content")
    file_path = str(p)

    assert os.path.isfile(file_path)

    functions.remove_local_file(file_path)

    assert not os.path.isfile(file_path)
