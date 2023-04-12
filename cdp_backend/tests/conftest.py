#!/usr/bin/env python

"""
Configuration for tests! There are a whole list of hooks you can define in this file to
run before, after, or to mutate how tests run. Commonly for most of our work, we use
this file to define top level fixtures that may be needed for tests throughout multiple
test files.

In this case, while we aren't using this fixture in our tests, the prime use case for
something like this would be when we want to preload a file to be used in multiple
tests. File reading can take time, so instead of re-reading the file for each test,
read the file once then use the loaded content.

Docs: https://docs.pytest.org/en/latest/example/simple.html
      https://docs.pytest.org/en/latest/plugins.html#requiring-loading-plugins-in-a-test-module-or-conftest-file
"""

from pathlib import Path

import pytest


@pytest.fixture
def resources_dir() -> Path:
    return Path(__file__).parent / "resources"


EXAMPLE_VIDEO_FILENAME = "example_video.mp4"
EXAMPLE_MKV_VIDEO_FILENAME = "example_video.mkv"
EXAMPLE_VIDEO_HD_FILENAME = "example_video_large.mp4"
EXAMPLE_YOUTUBE_VIDEO_EMBEDDED = "https://www.youtube.com/embed/XALBGkjkUPQ"
EXAMPLE_YOUTUBE_VIDEO_PARAMETER = "https://www.youtube.com/watch?v=XALBGkjkUPQ"
EXAMPLE_YOUTUBE_VIDEO_SHORT = "https://youtu.be/watch?v=XALBGkjkUPQ"
EXAMPLE_M3U8_PLAYLIST_URI = (
    "https://archive-stream.granicus.com/OnDemand/_definst_/mp4:oakland/"
    "oakland_fa356edd-b6a3-4532-8118-3ce4881783f4.mp4/playlist.m3u8"
)

# City of Versailles, Kentucky
EXAMPLE_VIMEO = "https://vimeo.com/503166067"

# City of Chicago, Illinois
EXAMPLE_VIMEO_SHOWCASE = "https://vimeo.com/showcase/6277394/video/722690793"

EXAMPLE_DOCX_ONE_WORD = "example_one_word.docx"
EXAMPLE_DOCX_HEADER = "example_header_only.docx"
EXAMPLE_DOCX_FOOTER = "example_footer_only.docx"
EXAMPLE_DOCX_LARGE = "example_multi_page.docx"
EXAMPLE_DOC_LARGE = "example_multi_page.doc"
EXAMPLE_DOC_FOOTER = "example_footer_only.doc"
EXAMPLE_PPTX_ONE_SLIDE = "example_one_slide.pptx"
EXAMPLE_PPTX_LARGE = "example_multi_slide.pptx"
EXAMPLE_PDF_ONE_WORD = "example_one_word.pdf"


@pytest.fixture
def example_video(resources_dir: Path) -> Path:
    return resources_dir / EXAMPLE_VIDEO_FILENAME
