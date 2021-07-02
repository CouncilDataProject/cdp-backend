#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
from typing import Callable, List
from unittest import mock
from unittest.mock import MagicMock

import pytest
from prefect import Flow

from cdp_backend.pipeline import event_gather_pipeline as pipeline
from cdp_backend.pipeline.ingestion_models import (
    EXAMPLE_MINIMAL_EVENT,
    EventIngestionModel,
)
from cdp_backend.pipeline.mock_get_events import get_events as rand_get_events


def min_get_events() -> List[EventIngestionModel]:
    event = EXAMPLE_MINIMAL_EVENT
    event.sessions[0].session_datetime = datetime(2019, 4, 13)
    return [event]


@pytest.mark.parametrize("func", [min_get_events, rand_get_events])
def test_create_event_gather_flow(func: Callable) -> None:
    flow = pipeline.create_event_gather_flow(
        get_events_func=func,
        credentials_file="/fake/credentials/path",
        bucket="bucket",
    )
    assert isinstance(flow, Flow)


@mock.patch("cdp_backend.file_store.functions.remove_local_file_task")
@mock.patch("cdp_backend.database.functions.upload_db_model_task")
@mock.patch("cdp_backend.database.functions.create_file")
@mock.patch("cdp_backend.file_store.functions.create_filename_from_filepath")
@mock.patch("cdp_backend.utils.file_utils.hash_file_contents_task")
@mock.patch("cdp_backend.utils.file_utils.join_strs_and_extension")
@mock.patch("cdp_backend.utils.file_utils.split_audio_task")
@mock.patch("cdp_backend.utils.file_utils.resource_copy_task")
@mock.patch("cdp_backend.file_store.functions.upload_file_task")
@mock.patch("cdp_backend.file_store.functions.get_file_uri_task")
@pytest.mark.parametrize(
    "video_uri, get_file_uri_value, upload_file_value, expected_audio_uri",
    [
        # TODO add test case for when audio uri doesn't exist
        ("video_uri", None, "audio_uri", "audio_uri")
    ],
)
def test_create_or_get_audio(
    mock_get_file_uri: MagicMock,
    mock_upload_file: MagicMock,
    mock_external_copy: MagicMock,
    mock_audio: MagicMock,
    mock_hash_file: MagicMock,
    mock_create_filename_from_parts: MagicMock,
    mock_create_filename: MagicMock,
    mock_create_file: MagicMock,
    mock_upload_db: MagicMock,
    mock_remove_file: MagicMock,
    video_uri: str,
    get_file_uri_value: str,
    upload_file_value: str,
    expected_audio_uri: str,
) -> None:
    mock_get_file_uri.return_value = get_file_uri_value
    mock_external_copy.return_value = "mock value"
    mock_hash_file.return_value = "abc"
    mock_create_filename_from_parts.return_value = "abc_audio.wav"
    mock_audio.return_value = ("audio path", "err", "out")
    mock_upload_file.return_value = upload_file_value

    actual_audio_uri = pipeline.create_or_get_audio(
        video_uri=video_uri,
        bucket="bucket",
        credentials_file="/fake/credentials/path",
    )

    assert expected_audio_uri == actual_audio_uri
