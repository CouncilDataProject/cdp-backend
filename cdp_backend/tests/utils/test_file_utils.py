#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import sys
from pathlib import Path
from typing import BinaryIO, Generator, List, Optional
from unittest import mock

import pytest
from py._path.local import LocalPath

from cdp_backend.pipeline.transcript_model import EXAMPLE_TRANSCRIPT
from cdp_backend.utils import file_utils
from cdp_backend.utils.file_utils import external_resource_copy

#############################################################################


@pytest.fixture
def example_video(resources_dir: Path) -> Path:
    return resources_dir / "example_video.mp4"


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


def test_hash_file_contents(tmpdir: LocalPath) -> None:
    test_file = Path(tmpdir) / "a.txt"

    with open(test_file, "w") as open_f:
        open_f.write("hello")

    hash_a = file_utils.hash_file_contents_task.run(  # type: ignore
        str(test_file.absolute())
    )

    with open(test_file, "w") as open_f:
        open_f.write("world")

    hash_b = file_utils.hash_file_contents_task.run(  # type: ignore
        str(test_file.absolute())
    )

    assert hash_a != hash_b


@pytest.mark.parametrize(
    "parts, extension, delimiter, expected",
    [
        (["hello", "world"], "mp4", "_", "hello_world.mp4"),
        (["a", "b", "c"], "wav", "-", "a-b-c.wav"),
        (["single"], "png", "***", "single.png"),
    ],
)
def test_join_strs_and_extension(
    parts: List[str], extension: str, delimiter: str, expected: str
) -> None:
    result = file_utils.join_strs_and_extension.run(  # type: ignore
        parts=parts, extension=extension, delimiter=delimiter
    )
    assert result == expected


@pytest.mark.parametrize(
    "audio_save_path",
    [
        ("test.wav"),
        (Path("test.wav")),
        pytest.param(__file__, marks=pytest.mark.raises(exception=FileExistsError)),
        pytest.param(
            Path(__file__), marks=pytest.mark.raises(exception=FileExistsError)
        ),
        pytest.param(
            Path(__file__).parent, marks=pytest.mark.raises(exception=IsADirectoryError)
        ),
    ],
)
def test_split_audio(
    tmpdir: LocalPath,
    example_video: str,
    audio_save_path: str,
) -> None:
    # Append save name to tmpdir
    tmp_dir_audio_save_path = Path(tmpdir) / Path(audio_save_path).resolve()

    # Mock split
    with mock.patch("ffmpeg.run") as mocked_ffmpeg:
        mocked_ffmpeg.return_value = (b"OUTPUT", b"ERROR")
        try:
            audio_file, stdout_log, stderr_log = file_utils.split_audio(
                video_read_path=example_video,
                audio_save_path=str(tmp_dir_audio_save_path),
            )

            assert str(tmp_dir_audio_save_path) == audio_file
            assert str(tmp_dir_audio_save_path.with_suffix(".out")) == stdout_log
            assert str(tmp_dir_audio_save_path.with_suffix(".err")) == stderr_log

        except Exception as e:
            raise e


@pytest.mark.skipif(sys.platform.startswith("win"), reason="tmpdir windows trouble")
@pytest.mark.parametrize("save_path", [("transcript_path")])
def test_save_data_as_json_file(
    tmpdir: LocalPath,
    save_path: str,
) -> None:

    expected_save_path = str(Path(tmpdir) / Path(save_path + ".json").resolve())

    assert expected_save_path == (
        file_utils.save_dataclass_as_json_file.run(  # type: ignore
            EXAMPLE_TRANSCRIPT, save_path
        )
    )


@pytest.mark.parametrize(
    "file_uri, expected",
    [
        ("gs://file_uri.txt", "file_uri.txt"),
    ],
)
def test_create_filename_from_file_uri(
    file_uri: str,
    expected: str,
) -> None:
    assert (
        file_utils.create_filename_from_file_uri.run(file_uri)  # type: ignore
        == expected
    )
