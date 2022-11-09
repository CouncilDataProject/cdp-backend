#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import random
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional
from unittest import mock

import ffmpeg
import imageio
import pytest

from cdp_backend.utils import file_utils
from cdp_backend.utils.file_utils import (
    MAX_THUMBNAIL_HEIGHT,
    MAX_THUMBNAIL_WIDTH,
    caption_is_valid,
    resource_copy,
)

from .. import test_utils
from ..conftest import (
    EXAMPLE_MKV_VIDEO_FILENAME,
    EXAMPLE_VIDEO_FILENAME,
    EXAMPLE_VIDEO_HD_FILENAME,
    EXAMPLE_VIMEO,
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


# Type ignore because changing tmpdir typing
def test_resource_copy(tmpdir, example_video: Path) -> None:  # type: ignore
    save_path = tmpdir / EXAMPLE_VIDEO_FILENAME
    resource_copy(str(example_video), save_path)


# Type ignore because changing tmpdir typing
def test_hash_file_contents(tmpdir) -> None:  # type: ignore
    test_file = Path(tmpdir) / "a.txt"

    with open(test_file, "w") as open_f:
        open_f.write("hello")

    hash_a = file_utils.hash_file_contents(str(test_file.absolute()))

    with open(test_file, "w") as open_f:
        open_f.write("world")

    hash_b = file_utils.hash_file_contents(str(test_file.absolute()))

    assert hash_a != hash_b


# Type ignore because changing tmpdir typing
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
@pytest.mark.parametrize(
    "start_time, end_time",
    [
        (None, None),
        ("1", "10"),
        (None, "10"),
        ("1", None),
        ("0", "0"),
        ("1", "0"),
    ],
)
def test_split_audio(  # type: ignore
    tmpdir,
    example_video: str,
    start_time: str,
    end_time: str,
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
                start_time=start_time,
                end_time=end_time,
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
        # (EXAMPLE_VIMEO_SHOWCASE, Path("722690793") / "722690793.mp4"),
        # (EXAMPLE_M3U8_PLAYLIST_URI, None),
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


@pytest.mark.parametrize(
    "start_time, end_time",
    [
        ("1:25", "1:35"),
        ("1:25", "1:35"),
        ("01:10", "01:14"),
        ("00:01:01", "00:01:03"),
    ],
)
@pytest.mark.parametrize(
    "output_format",
    ["mp4", "mp3"],
)
def test_clip_and_reformat_video(
    resources_dir: Path,
    start_time: str,
    end_time: str,
    output_format: str,
) -> None:
    expected_outfile = Path(f"test-clipped.{output_format}")
    try:
        os.remove(expected_outfile)
    except FileNotFoundError:
        pass
    outfile = file_utils.clip_and_reformat_video(
        resources_dir / EXAMPLE_VIDEO_FILENAME,
        start_time=start_time,
        end_time=end_time,
        output_path=expected_outfile,
        output_format=output_format,
    )
    assert outfile.exists()
    assert outfile == expected_outfile
    os.remove(outfile)


@pytest.mark.parametrize(
    "video_uri, caption_uri, end_time, is_resource, expected",
    [
        # the video is about 3 minutes and boston_captions.vtt is about 1 minute
        (EXAMPLE_VIDEO_FILENAME, "boston_captions.vtt", 120, True, False),
        (EXAMPLE_VIDEO_FILENAME, "boston_captions.vtt", 60, True, True),
        (
            EXAMPLE_VIDEO_FILENAME,
            # about 30 seconds
            "https://gist.github.com/dphoria/d3f35b5509b784ccd14b7efdc67df752/raw/"
            "c18fc459c62ff7530536ba19d08021682627c18a/sample.vtt",
            30,
            False,
            True,
        ),
    ],
)
def test_caption_is_valid(
    resources_dir: Path,
    video_uri: str,
    caption_uri: str,
    end_time: int,
    is_resource: bool,
    expected: bool,
) -> None:
    with TemporaryDirectory() as dir_path:
        temp_video = str(Path(dir_path) / f"caption-test-{end_time}.mp4")
        ffmpeg.input(str(resources_dir / video_uri)).output(
            temp_video, codec="copy", t=end_time
        ).run(overwrite_output=True)

        if is_resource:
            caption_uri = str(resources_dir / caption_uri)

        print(temp_video)
        assert caption_is_valid(temp_video, caption_uri) == expected
