#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import random
import sys
from pathlib import Path
from typing import Optional
from unittest import mock

import imageio
import pytest
from py._path.local import LocalPath

from cdp_backend.utils import file_utils
from cdp_backend.utils.file_utils import (
    MAX_THUMBNAIL_HEIGHT,
    MAX_THUMBNAIL_WIDTH,
    resource_copy,
)

from .. import test_utils
from ..conftest import (
    EXAMPLE_M3U8_PLAYLIST_URI,
    EXAMPLE_MKV_VIDEO_FILENAME,
    EXAMPLE_VIDEO_FILENAME,
    EXAMPLE_VIDEO_HD_FILENAME,
    EXAMPLE_VIMEO,
    EXAMPLE_VIMEO_SHOWCASE,
    EXAMPLE_YOUTUBE_VIDEO_EMBEDDED,
    EXAMPLE_YOUTUBE_VIDEO_PARAMETER,
    EXAMPLE_YOUTUBE_VIDEO_SHORT,
)

#############################################################################


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


def test_resource_copy(tmpdir: LocalPath, example_video: Path) -> None:
    save_path = tmpdir / EXAMPLE_VIDEO_FILENAME
    resource_copy(str(example_video), save_path)


def test_hash_file_contents(tmpdir: LocalPath) -> None:
    test_file = Path(tmpdir) / "a.txt"

    with open(test_file, "w") as open_f:
        open_f.write("hello")

    hash_a = file_utils.hash_file_contents(str(test_file.absolute()))

    with open(test_file, "w") as open_f:
        open_f.write("world")

    hash_b = file_utils.hash_file_contents(str(test_file.absolute()))

    assert hash_a != hash_b


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


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="File removal for test cleanup sometimes fails on Windows",
)
@pytest.mark.parametrize(
    "video_url, session_content_hash, seconds, expected",
    [
        (EXAMPLE_VIDEO_FILENAME, "example2", 45, "example2-static-thumbnail.png"),
        (EXAMPLE_VIDEO_FILENAME, "example3", 999999, "example3-static-thumbnail.png"),
        (EXAMPLE_VIDEO_HD_FILENAME, "example4", 9, "example4-static-thumbnail.png"),
        pytest.param(
            "fake.mp4",
            "example",
            30,
            "",
            marks=pytest.mark.raises(exception=FileNotFoundError),
        ),
        pytest.param(
            "fake_creds.json",
            "example",
            30,
            "",
            marks=pytest.mark.raises(exception=ValueError),
        ),
    ],
)
def test_static_thumbnail_generator(
    resources_dir: Path,
    video_url: Path,
    session_content_hash: str,
    seconds: int,
    expected: str,
) -> None:
    video_url = resources_dir / video_url

    result = file_utils.get_static_thumbnail(
        str(video_url), session_content_hash, seconds
    )
    assert result == expected

    assert Path(result).stat().st_size > 0

    image = imageio.imread(result)
    assert image.shape[0] <= MAX_THUMBNAIL_HEIGHT
    assert image.shape[1] <= MAX_THUMBNAIL_WIDTH

    os.remove(result)


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="File removal for test cleanup sometimes fails on Windows",
)
@pytest.mark.parametrize(
    "video_url, session_content_hash, num_frames, expected",
    [
        (EXAMPLE_VIDEO_FILENAME, "example2", 15, "example2-hover-thumbnail.gif"),
        (EXAMPLE_VIDEO_HD_FILENAME, "example3", 2, "example3-hover-thumbnail.gif"),
        pytest.param(
            "fake.mp4",
            "example",
            10,
            "",
            marks=pytest.mark.raises(exception=FileNotFoundError),
        ),
        pytest.param(
            "fake_creds.json",
            "example",
            10,
            "",
            marks=pytest.mark.raises(exception=ValueError),
        ),
    ],
)
def test_hover_thumbnail_generator(
    resources_dir: Path,
    video_url: Path,
    session_content_hash: str,
    num_frames: int,
    expected: str,
) -> None:
    video_url = resources_dir / video_url

    # Set random seed to get consistent result
    random.seed(42)

    result = file_utils.get_hover_thumbnail(
        str(video_url), session_content_hash, num_frames
    )
    assert result == expected

    reader = imageio.get_reader(result)
    assert reader._length == num_frames

    image = imageio.imread(result)
    assert image.shape[0] <= MAX_THUMBNAIL_HEIGHT
    assert image.shape[1] <= MAX_THUMBNAIL_WIDTH

    os.remove(result)


@pytest.mark.skipif(
    not test_utils.internet_is_available(),
    reason="No internet connection",
)
@pytest.mark.parametrize(
    "video_uri, expected",
    [
        (EXAMPLE_MKV_VIDEO_FILENAME, EXAMPLE_VIDEO_FILENAME),
    ],
)
def test_convert_video_to_mp4(
    resources_dir: Path,
    video_uri: str,
    expected: str,
) -> None:
    filepath = str(resources_dir / video_uri)
    assert file_utils.convert_video_to_mp4(filepath) == str(resources_dir / expected)


@pytest.mark.skipif(
    not test_utils.internet_is_available(),
    reason="No internet connection",
)
@pytest.mark.parametrize(
    "uri, expected",
    [
        (EXAMPLE_YOUTUBE_VIDEO_EMBEDDED, "XALBGkjkUPQ.mp4"),
        (EXAMPLE_YOUTUBE_VIDEO_PARAMETER, "XALBGkjkUPQ.mp4"),
        (EXAMPLE_YOUTUBE_VIDEO_SHORT, "XALBGkjkUPQ.mp4"),
        (EXAMPLE_VIMEO, Path("503166067") / "503166067.mp4"),
        (EXAMPLE_VIMEO_SHOWCASE, Path("722690793") / "722690793.mp4"),
        (EXAMPLE_M3U8_PLAYLIST_URI, None),
    ],
)
def test_remote_resource_copy(
    resources_dir: Path,
    uri: str,
    expected: Optional[str],
) -> None:
    actual_uri = file_utils.resource_copy(uri, resources_dir, True)
    if expected:
        expected_uri = str(resources_dir / expected)
        assert actual_uri == expected_uri

    assert Path(actual_uri).exists()
    assert Path(actual_uri).is_file()

    os.remove(actual_uri)


def test_invalid_uri() -> None:
    with pytest.raises(Exception) as e:
        file_utils.resource_copy("https://vimeo.com/fakeuri")
    assert e.type == ValueError
    assert (
        str(e.value)
        == "Could not extract video id from uri: 'https://vimeo.com/fakeuri'"
    )
