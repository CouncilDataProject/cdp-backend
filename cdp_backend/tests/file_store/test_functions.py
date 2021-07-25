#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
from typing import Optional
from unittest import mock

import pytest
from gcsfs import GCSFileSystem
from py._path.local import LocalPath

from cdp_backend.file_store import functions

###############################################################################

FILENAME = "file.txt"
BUCKET = "bucket"
FILEPATH = "fake/path/" + FILENAME
SAVE_NAME = "fakeSaveName"
EXISTING_FILE_URI = "gs://bucket/existing_file.json"
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
    expected: Optional[str],
) -> None:
    with mock.patch("gcsfs.credentials.GoogleCredentials.connect"):
        with mock.patch("gcsfs.GCSFileSystem.exists") as mock_exists:
            mock_exists.return_value = exists

            assert expected == functions.get_file_uri(bucket, filename, "path/to/creds")


@pytest.mark.parametrize(
    "bucket, filepath, save_name, remove_local, existing_file_uri, expected",
    [
        (BUCKET, FILEPATH, SAVE_NAME, True, EXISTING_FILE_URI, EXISTING_FILE_URI),
        (BUCKET, FILEPATH, SAVE_NAME, False, EXISTING_FILE_URI, EXISTING_FILE_URI),
        (BUCKET, FILEPATH, None, False, None, GCS_FILE_URI),
        (BUCKET, FILEPATH, None, True, None, GCS_FILE_URI),
    ],
)
def test_upload_file(
    bucket: str,
    filepath: str,
    save_name: Optional[str],
    remove_local: bool,
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
                        "path/to/creds", bucket, filepath, save_name, remove_local
                    )


def test_remove_local_file(tmpdir: LocalPath) -> None:
    p = tmpdir.mkdir("sub").join("hello.txt")
    p.write("content")
    file_path = str(p)

    assert os.path.isfile(file_path)

    functions.remove_local_file(file_path)

    assert not os.path.isfile(file_path)
