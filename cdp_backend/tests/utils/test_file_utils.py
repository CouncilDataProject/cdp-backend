#!/usr/bin/env python

from __future__ import annotations

import os
import random
import sys
import time
from pathlib import Path
from unittest import mock

import imageio
import pytest

from cdp_backend.utils import file_utils
from cdp_backend.utils.file_utils import (
    MAX_THUMBNAIL_HEIGHT,
    MAX_THUMBNAIL_WIDTH,
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
    "path, stem, expected_result",
    [
        (Path("file.ext"), "new", "new.ext"),
    ],
)
def test_with_stem(path: Path, stem: str, expected_result: str) -> None:
    new_path = file_utils.with_stem(path, stem)
    assert str(new_path) == expected_result


@pytest.mark.parametrize(
    "path, addition, expected_result",
    [
        (Path("file.ext"), "-new", "file-new.ext"),
    ],
)
def test_append_to_stem(path: Path, addition: str, expected_result: str) -> None:
    new_path = file_utils.append_to_stem(path, addition)
    assert str(new_path) == expected_result


@pytest.mark.parametrize(
    "path, stem, expected_result",
    [
        (Path("file.ext"), "new", "new.ext"),
    ],
)
def test_rename_with_stem(path: Path, stem: str, expected_result: str) -> None:
    file = open(path, "w")
    file.close()
    new_path = file_utils.rename_with_stem(path, stem)
    assert str(new_path) == expected_result
    assert new_path.exists()
    os.remove(new_path)


@pytest.mark.parametrize(
    "path, addition, expected_result",
    [
        (Path("file.ext"), "-new", "file-new.ext"),
    ],
)
def test_rename_append_to_stem(path: Path, addition: str, expected_result: str) -> None:
    file = open(path, "w")
    file.close()
    new_path = file_utils.rename_append_to_stem(path, addition)
    assert str(new_path) == expected_result
    assert new_path.exists()
    os.remove(new_path)


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
def test_get_media_type(uri: str, expected_result: str | None) -> None:
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


@pytest.mark.parametrize("video_filename", [(EXAMPLE_VIDEO_FILENAME)])
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
def test_split_audio(  # type: ignore
    tmpdir: Path,
    resources_dir: Path,
    video_filename: str,
    audio_save_path: str,
) -> None:
    # Append save name to tmpdir
    tmp_dir_audio_save_path = Path(tmpdir) / Path(audio_save_path).resolve()
    example_video = str(resources_dir / video_filename)

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

            os.remove(audio_file)
            os.remove(stdout_log)
            os.remove(stderr_log)

        except Exception as e:
            raise e


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="File removal for test cleanup sometimes fails on Windows",
)
@pytest.mark.parametrize(
    "video_filename, session_content_hash, seconds, expected",
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
    video_filename: str,
    session_content_hash: str,
    seconds: int,
    expected: str,
) -> None:
    video_path = resources_dir / video_filename

    result = file_utils.get_static_thumbnail(
        str(video_path), session_content_hash, seconds
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
    "video_filename, session_content_hash, num_frames, expected",
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
    video_filename: str,
    session_content_hash: str,
    num_frames: int,
    expected: str,
) -> None:
    video_path = resources_dir / video_filename

    # Set random seed to get consistent result
    random.seed(42)

    result = file_utils.get_hover_thumbnail(
        str(video_path), session_content_hash, num_frames
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
    "video_filename, expected",
    [
        (EXAMPLE_MKV_VIDEO_FILENAME, "test-" + EXAMPLE_VIDEO_FILENAME),
    ],
)
@pytest.mark.parametrize(
    "start_time, end_time",
    [
        ("1", "3"),
        (None, "3"),
        ("2:58", None),
    ],
)
def test_convert_video_to_mp4(
    resources_dir: Path,
    video_filename: str,
    expected: str,
    start_time: str | None,
    end_time: str | None,
) -> None:
    filepath = resources_dir / video_filename
    outfile = resources_dir / expected
    outfile = file_utils.convert_video_to_mp4(filepath, start_time, end_time, outfile)
    assert outfile == resources_dir / expected
    assert outfile.exists()
    os.remove(outfile)


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
    expected: str | None,
) -> None:
    actual_uri = file_utils.resource_copy(uri, resources_dir, True)
    if expected:
        expected_uri = str(resources_dir / expected)
        assert actual_uri == expected_uri

    assert Path(actual_uri).exists()
    assert Path(actual_uri).is_file()

    os.remove(actual_uri)

    time.sleep(5)


def test_invalid_uri() -> None:
    with pytest.raises(Exception) as e:
        file_utils.resource_copy("https://vimeo.com/fakeuri")
    assert e.type == ValueError
    assert (
        str(e.value)
        == "Could not extract video id from uri: 'https://vimeo.com/fakeuri'"
    )


@pytest.mark.parametrize(
    "video_filename, start_time, end_time, output_format, output_filename",
    [
        ([EXAMPLE_VIDEO_FILENAME], "1:25", "1:35", "mp4", "test-clipped.mp4"),
        ([EXAMPLE_VIDEO_FILENAME], "1:25", "1:35", "mp4", "test-clipped.mp4"),
        ([EXAMPLE_VIDEO_FILENAME], "01:10", "01:14", "mp4", "test-clipped.mp4"),
        ([EXAMPLE_VIDEO_FILENAME], "00:01:01", "00:01:03", "mp3", None),
    ],
)
def test_clip_and_reformat_video(
    resources_dir: Path,
    video_filename: str,
    start_time: str,
    end_time: str,
    output_format: str,
    output_filename: str,
) -> None:
    expected_outfile = None
    if output_filename:
        expected_outfile = Path(f"{output_filename}")
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
    assert outfile == (expected_outfile or outfile)
    os.remove(outfile)
