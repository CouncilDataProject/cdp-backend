#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO, Generator, Optional
from unittest import mock

import pytest
from py._path.local import LocalPath

from cdp_backend.utils import file_utils
from cdp_backend.utils.file_utils import external_resource_copy

#############################################################################


@pytest.fixture
def example_video(data_dir: Path) -> Path:
    return data_dir / "example_video.mp4"


class MockedResponse:
    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath
        self.opened = open(self.filepath, "rb")

    def __enter__(self) -> MockedResponse:
        return self

    def __exit__(self, exception_type, exception_value, tb):  # type: ignore
        self.opened.close()

    def raise_for_status(self) -> bool:
        return True

    @property
    def raw(self) -> BinaryIO:
        return self.opened


@pytest.fixture
def mocked_request(example_video: Path) -> Generator:
    with mock.patch("requests.get") as MockRequest:
        MockRequest.return_value = MockedResponse(example_video)
        yield MockRequest


@pytest.mark.parametrize(
    "uri, expected_result",
    [
        ("https://some.site.co/index.html", "text/html"),
        ("https://some.site.co/data.json", "application/json"),
        ("https://some.site.co/image.png", "image/png"),
        ("https://some.site.co/image.tiff", "image/tiff"),
        ("https://some.site.co/report.pdf", "application/pdf"),
        ("https://some.site.co/image.unknownformat", None),
        ("file:///some/dir/index.html", "text/html"),
        ("file:///some/dir/data.json", "application/json"),
        ("file:///some/dir/image.png", "image/png"),
        ("file:///some/dir/image.tiff", "image/tiff"),
        ("file:///some/dir/report.pdf", "application/pdf"),
        ("file:///some/dir/image.unknownformat", None),
    ],
)
def test_get_media_type(uri: str, expected_result: Optional[str]) -> None:
    actual_result = file_utils.get_media_type(uri)
    assert actual_result == expected_result


def test_external_resource_copy(tmpdir: LocalPath, mocked_request: Generator) -> None:
    save_path = tmpdir / "tmpcopy.mp4"
    external_resource_copy("https://doesntmatter.com/example.mp4", save_path)
