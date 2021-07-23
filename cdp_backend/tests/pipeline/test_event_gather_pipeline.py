#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock

import pytest
from prefect import Flow

from cdp_backend.pipeline import event_gather_pipeline as pipeline
from cdp_backend.pipeline.mock_get_events import (
    FILLED_FLOW_CONFIG,
    MANY_FLOW_CONFIG,
    MINIMAL_FLOW_CONFIG,
    RANDOM_FLOW_CONFIG,
)
from cdp_backend.pipeline.pipeline_config import EventGatherPipelineConfig

#############################################################################

VIDEO_CONTENT_HASH = "7490ea6cf56648d60a40dd334e46e5d7de0f31dde0c7ce4d85747896fdd2ab42"

#############################################################################


@pytest.mark.parametrize(
    "config",
    [FILLED_FLOW_CONFIG, MANY_FLOW_CONFIG, MINIMAL_FLOW_CONFIG, RANDOM_FLOW_CONFIG],
)
def test_create_event_gather_flow(config: EventGatherPipelineConfig) -> None:
    flow = pipeline.create_event_gather_flow(config=config)
    assert isinstance(flow, Flow)


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Path handling / splitting failing due to windows path separator",
)
@mock.patch("cdp_backend.file_store.functions.get_file_uri")
@mock.patch("cdp_backend.file_store.functions.upload_file")
@pytest.mark.parametrize(
    "get_file_uri_value, audio_upload_file_return, expected_session_content_hash",
    [
        (
            None,
            f"fake://{VIDEO_CONTENT_HASH}-audio.wav",
            VIDEO_CONTENT_HASH,
        ),
        (
            f"fake://{VIDEO_CONTENT_HASH}-audio.wav",
            f"fake://{VIDEO_CONTENT_HASH}-audio.wav",
            VIDEO_CONTENT_HASH,
        ),
    ],
)
def test_get_video_and_split_audio(
    mock_get_file_uri: MagicMock,
    mock_upload_file: MagicMock,
    get_file_uri_value: str,
    audio_upload_file_return: str,
    expected_session_content_hash: str,
    example_video: Path,
) -> None:
    mock_get_file_uri.return_value = get_file_uri_value
    mock_upload_file.return_value = audio_upload_file_return

    (
        session_content_hash,
        audio_uri,
    ) = pipeline.get_video_and_split_audio.run(  # type: ignore
        video_uri=str(example_video),
        bucket="bucket",
        credentials_file="/fake/credentials/path",
    )

    # Check outputs
    assert session_content_hash == expected_session_content_hash
    assert audio_uri == audio_upload_file_return
