import os
from pathlib import Path

import pytest

from cdp_backend.pipeline.thumbnail_generator import (
    get_hover_thumbnail,
    get_static_thumbnail,
)

test_data_directory = "./cdp_backend/tests/data/"

"""
Static thumbnail generator tests

The static thumbnail generator produces a png thumbnail for an mp4 video
"""


# Test if the static thumbnail generator can produce a thumbnail with the default
# timing
# The default timing is always 30 seconds into the video
def test_get_static_thumbnail_standard() -> None:
    assert (
        get_static_thumbnail(test_data_directory + "example_video.mp4")
        == test_data_directory + "example_video.png"
    )
    assert Path(test_data_directory + "example_video.png").stat().st_size > 0
    os.remove(test_data_directory + "example_video.png")


# Test if the static thumbnail generator can produce a thumbnail with a variable timing
# In this case, the timing is 45 seconds into the video
def test_get_static_thumbnail_different_time() -> None:
    assert (
        get_static_thumbnail(test_data_directory + "example_video.mp4", 45)
        == test_data_directory + "example_video.png"
    )
    assert Path(test_data_directory + "example_video.png").stat().st_size > 0
    os.remove(test_data_directory + "example_video.png")


# Test if the static thumbnail generator will raise an exception if the file does not
# exist
def test_get_static_thumbnail_nonexistent_file() -> None:
    with pytest.raises(Exception):
        get_static_thumbnail(test_data_directory + "nonexistent_video.mp4")


# Test if the static thumbnail generator will raise an exception if the file is not an
# mp4
def test_get_static_thumbnail_not_mp4() -> None:
    with pytest.raises(Exception):
        get_static_thumbnail(test_data_directory + "fake_creds.json")


"""
Hover thumbnail generator tests

The static thumbnail generator produces a gif thumbnail for an mp4 video
"""


# Test if the hover thumbnail generator can produce a thumbnail with the default number
# of frames (10)
def test_get_hover_thumbnail_standard() -> None:
    assert (
        get_hover_thumbnail(test_data_directory + "example_video.mp4")
        == test_data_directory + "example_video.gif"
    )
    assert Path(test_data_directory + "example_video.gif").stat().st_size > 0
    os.remove(test_data_directory + "example_video.gif")


# Test if the hover thumbnail generator can produce a thumbnail with a variable number
# of frames (10 in this case)
def test_get_hover_thumbnail_different_time() -> None:
    assert (
        get_hover_thumbnail(test_data_directory + "example_video.mp4", 45)
        == test_data_directory + "example_video.gif"
    )
    assert Path(test_data_directory + "example_video.gif").stat().st_size > 0
    os.remove(test_data_directory + "example_video.gif")


# Test if the hover thumbnail generator will raise an exception if the file does not
# exist
def test_get_hover_thumbnail_nonexistent_file() -> None:
    with pytest.raises(Exception):
        get_hover_thumbnail(test_data_directory + "nonexistent_video.mp4")


# Test if the hover thumbnail generator will raise an exception if the file is not an
# mp4
def test_get_hover_thumbnail_not_mp4() -> None:
    with pytest.raises(Exception):
        get_hover_thumbnail(test_data_directory + "fake_creds.json")
