#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
from typing import List
from unittest import mock
from unittest.mock import MagicMock

import pytest
from prefect import Flow
from py._path.local import LocalPath

from cdp_backend.database import models as db_models
from cdp_backend.pipeline import event_gather_pipeline as pipeline
from cdp_backend.pipeline.ingestion_models import (
    EXAMPLE_MINIMAL_EVENT,
    Body,
    EventIngestionModel,
    Session,
)

from ..database.test_functions import (
    assert_ingestion_and_db_models_equal,
    db_body,
    db_event,
    db_session,
    full_ingestion_body,
    full_ingestion_session,
    minimal_ingestion_body,
    minimal_ingestion_event,
    minimal_ingestion_session,
)

example_file = db_models.File()
example_file.name = "file name"
example_file.uri = "uri"


def mock_get_events_func() -> List[EventIngestionModel]:
    event = EXAMPLE_MINIMAL_EVENT
    event.sessions[0].session_datetime = datetime(2019, 4, 13)
    return [event]


def test_create_event_gather_flow() -> None:
    flow = pipeline.create_event_gather_flow(
        get_events_func=mock_get_events_func,
        credentials_file="/fake/credentials/path",
        bucket="bucket",
    )
    assert isinstance(flow, Flow)


@mock.patch("cdp_backend.file_store.functions.remove_local_file_task")
@mock.patch("cdp_backend.database.functions.upload_db_model_task")
@mock.patch("cdp_backend.pipeline.event_gather_pipeline.create_file")
@mock.patch("cdp_backend.pipeline.event_gather_pipeline.create_filename_from_filepath")
@mock.patch("cdp_backend.utils.file_utils.split_audio_task")
@mock.patch("cdp_backend.utils.file_utils.external_resource_copy_task")
@mock.patch("cdp_backend.file_store.functions.upload_file_task")
@mock.patch("cdp_backend.file_store.functions.get_file_uri_task")
@pytest.mark.parametrize(
    "key, video_uri, get_file_uri_value, upload_file_value, expected_audio_uri",
    [
        # TODO add test case for when audio uri doesn't exist
        ("123", "video_uri", None, "audio_uri", "audio_uri")
    ],
)
def test_create_or_get_audio(
    mock_get_file_uri: MagicMock,
    mock_upload_file: MagicMock,
    mock_external_copy: MagicMock,
    mock_audio: MagicMock,
    mock_create_filename: MagicMock,
    mock_create_file: MagicMock,
    mock_upload_db: MagicMock,
    mock_remove_file: MagicMock,
    key: str,
    video_uri: str,
    get_file_uri_value: str,
    upload_file_value: str,
    expected_audio_uri: str,
) -> None:
    mock_get_file_uri.return_value = get_file_uri_value
    mock_external_copy.return_value = "mock value"
    mock_audio.return_value = ("audio path", "err", "out")
    mock_upload_file.return_value = upload_file_value

    actual_audio_uri = pipeline.create_or_get_audio(
        key=key,
        video_uri=video_uri,
        bucket="bucket",
        credentials_file="/fake/credentials/path",
    )

    assert expected_audio_uri == actual_audio_uri


@pytest.mark.parametrize(
    "ingestion_model, expected",
    [
        (minimal_ingestion_body, db_body),
        (full_ingestion_body, db_body),
    ],
)
def test_create_body_from_ingestion_model(
    ingestion_model: Body,
    expected: db_models.Body,
) -> None:
    actual = pipeline.create_body_from_ingestion_model.run(  # type: ignore
        ingestion_model
    )

    assert_ingestion_and_db_models_equal(ingestion_model, expected, actual)


@pytest.mark.parametrize(
    "ingestion_model, expected",
    [
        (minimal_ingestion_event, db_event),
    ],
)
def test_create_event_from_ingestion_model(
    ingestion_model: EventIngestionModel,
    expected: db_models.Event,
) -> None:
    actual = pipeline.create_event_from_ingestion_model.run(  # type: ignore
        ingestion_model, db_body
    )

    assert_ingestion_and_db_models_equal(ingestion_model, expected, actual)

    assert expected.body_ref == actual.body_ref


@pytest.mark.parametrize(
    "ingestion_model, expected",
    [(minimal_ingestion_session, db_session), (full_ingestion_session, db_session)],
)
def test_create_session_from_ingestion_model(
    ingestion_model: Session,
    expected: db_models.Session,
) -> None:
    actual = pipeline.create_session_from_ingestion_model.run(  # type: ignore
        ingestion_model, db_event
    )

    assert_ingestion_and_db_models_equal(ingestion_model, expected, actual)

    assert expected.event_ref == actual.event_ref


def test_create_file() -> None:
    db_file = pipeline.create_file.run("file name", "uri")  # type: ignore

    assert example_file.name == db_file.name
    assert example_file.uri == db_file.uri


def test_create_filename_from_filepath(tmpdir: LocalPath) -> None:
    p = tmpdir.mkdir("sub").join("hello.txt")
    p.write("content")
    filepath = str(p)
    assert "hello.txt" == pipeline.create_filename_from_filepath.run(  # type: ignore
        filepath
    )
