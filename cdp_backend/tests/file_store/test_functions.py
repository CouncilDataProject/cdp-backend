#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
import sys
from tempfile import NamedTemporaryFile
from typing import Optional, Union
from unittest import mock

import pytest
from gcsfs import GCSFileSystem

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
    with mock.patch("gcsfs.GCSFileSystem.connect"):
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
    expected: Union[str, None],
) -> None:
    with mock.patch("gcsfs.GCSFileSystem.connect"):
        with mock.patch("gcsfs.GCSFileSystem.exists") as mock_exists:
            mock_exists.return_value = exists

            assert expected == functions.get_file_uri(
                functions.initialize_gcs_file_system("fake/path"), bucket, filename
            )

    return


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
    with mock.patch("gcsfs.GCSFileSystem") as mock_fs:
        with mock.patch(
            "cdp_backend.file_store.functions.get_file_uri"
        ) as mock_file_uri:
            with mock.patch("cdp_backend.file_store.functions.remove_local_file"):
                with mock.patch("pathlib.Path.resolve") as mock_path:
                    mock_file_uri.return_value = existing_file_uri
                    mock_path.return_value.name = FILENAME

                    assert expected == functions.upload_file(
                        mock_fs, bucket, filepath, save_name, remove_local
                    )

    return


@pytest.mark.skipif(
    sys.platform.startswith("win"), reason="TemporaryFile has issues on windows"
)
def test_remove_local_file() -> None:
    f = NamedTemporaryFile()
    f.write(b"Hello world!")

    assert os.path.isfile(f.name)

    functions.remove_local_file(f.name)

    assert not os.path.isfile(f.name)
