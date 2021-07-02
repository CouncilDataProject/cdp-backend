#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
from pathlib import Path
from typing import Callable, List
from unittest import mock
from unittest.mock import MagicMock

import pytest
from prefect import Flow
from py._path.local import LocalPath

from cdp_backend.database import models as db_models
from cdp_backend.pipeline import event_gather_pipeline as pipeline
from cdp_backend.pipeline import transcript_model
from cdp_backend.pipeline.ingestion_models import (
    EXAMPLE_MINIMAL_EVENT,
    EventIngestionModel,
)
from cdp_backend.pipeline.mock_get_events import get_events as rand_get_events
from cdp_backend.tests.database.test_functions import assert_db_models_equality


@pytest.fixture
def fake_creds_path(resources_dir: Path) -> Path:
    return resources_dir / "fake_creds.json"


def min_get_events() -> List[EventIngestionModel]:
    event = EXAMPLE_MINIMAL_EVENT
    event.sessions[0].session_datetime = datetime(2019, 4, 13)
    return [event]


@pytest.mark.parametrize("func", [min_get_events, rand_get_events])
def test_create_event_gather_flow(func: Callable, tmpdir: LocalPath) -> None:
    flow = pipeline.create_event_gather_flow(
        get_events_func=func,
        credentials_file=str(tmpdir),
        bucket="bucket",
    )
    assert isinstance(flow, Flow)


@mock.patch("cdp_backend.pipeline.event_gather_pipeline.create_transcript")
@mock.patch("cdp_backend.pipeline.event_gather_pipeline.task_result_exists")
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
    "video_uri, get_file_uri_value, upload_file_value, expected_transcript",
    [
        # TODO add test case for when audio uri doesn't exist
        ("video_uri", None, "audio_uri", db_models.Transcript())
    ],
)
def test_create_audio_and_transcript(
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
    mock_task_result_exists: MagicMock,
    mock_create_transcript: MagicMock,
    video_uri: str,
    get_file_uri_value: str,
    upload_file_value: str,
    expected_transcript: db_models.Transcript,
) -> None:
    mock_get_file_uri.return_value = get_file_uri_value
    mock_external_copy.return_value = "mock value"
    mock_hash_file.return_value = "abc"
    mock_create_filename_from_parts.return_value = "abc_audio.wav"
    mock_audio.return_value = ("audio path", "err", "out")
    mock_upload_file.return_value = upload_file_value
    mock_create_transcript.return_value = db_models.Transcript()
    mock_task_result_exists.return_value = True

    actual_audio_and_transcript = pipeline.create_audio_and_transcript(
        video_uri=video_uri,
        bucket="bucket",
        credentials_file="/fake/credentials/path",
        session_ref=db_models.Session.Example(),
    )

    # Expected output
    expected_audio_and_transcript = (upload_file_value, expected_transcript)

    # Check audio_uri and transcript
    assert expected_audio_and_transcript[0] == actual_audio_and_transcript[0]

    assert_db_models_equality(
        expected_audio_and_transcript[1], actual_audio_and_transcript[1], True
    )


@mock.patch("cdp_backend.database.functions.create_transcript")
@mock.patch("cdp_backend.database.functions.upload_db_model_task")
@mock.patch("cdp_backend.database.functions.create_file")
@mock.patch("cdp_backend.utils.file_utils.create_filename_from_file_uri")
@mock.patch("cdp_backend.file_store.functions.upload_file_task")
@mock.patch("cdp_backend.utils.file_utils.save_dataclass_as_json_file")
@mock.patch("cdp_backend.sr_models.sr_functions.transcribe_task")
@pytest.mark.parametrize(
    "transcript, save_path, transcript_uri, db_file, db_file_ref, db_transcript, db_transcript_ref",  # noqa: E501
    [
        # TODO add test case for when audio uri doesn't exist
        (
            transcript_model.EXAMPLE_TRANSCRIPT,
            "save_path",
            "transcript_uri",
            db_models.File(),
            None,
            db_models.Transcript(),
            db_models.Transcript(),
        )
    ],
)
def test_create_transcript(
    mock_transcribe_task: MagicMock,
    mock_save_as_json_task: MagicMock,
    mock_upload_file_task: MagicMock,
    mock_create_filename_task: MagicMock,
    mock_create_file_task: MagicMock,
    mock_upload_db_model_task: MagicMock,
    mock_create_transcript: MagicMock,
    transcript: transcript_model.Transcript,
    save_path: str,
    transcript_uri: str,
    db_file: db_models.File,
    db_file_ref: db_models.Model,
    db_transcript: db_models.Transcript,
    db_transcript_ref: db_models.Model,
    fake_creds_path: str,
) -> None:
    mock_transcribe_task.return_value = transcript
    mock_save_as_json_task.return_value = save_path
    mock_upload_file_task.return_value = transcript_uri
    mock_create_file_task.return_value = db_file
    mock_upload_db_model_task.return_value = db_transcript_ref
    mock_create_transcript.return_value = db_transcript

    assert db_transcript_ref == pipeline.create_transcript(
        "audio_uri", db_models.Session(), "bucket", fake_creds_path
    )


def test_task_result_exists() -> None:
    assert pipeline.task_result_exists.run(1) is True  # type: ignore
    assert pipeline.task_result_exists.run(None) is False  # type: ignore
