#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cdp_backend.database.models as db_models
from cdp_backend.database.validators import UniquenessValidation
import cdp_backend.pipeline.cdp_event_gather_pipeline as pipeline
import cdp_backend.pipeline.ingestion_models as ingestion_models
from cdp_backend.pipeline.ingestion_models import (
    Body,
    EventIngestionModel,
    EXAMPLE_MINIMAL_EVENT,
    Session,
)

from datetime import datetime
from fireo.models import Model
from typing import Any, List
from prefect import Flow
from unittest import mock
import pytest


db_body = db_models.Body.Example()
db_body_extra = db_models.Body.Example()

db_event = db_models.Event.Example()
db_event.body_ref = db_body

db_session = db_models.Session.Example()
db_session.event_ref = db_event

minimal_ingestion_body = ingestion_models.Body(
    name=db_body.name, is_active=db_body.is_active
)
full_ingestion_body = ingestion_models.Body(
    name=db_body.name,
    is_active=db_body.is_active,
    start_datetime=db_body.start_datetime,
    end_datetime=db_body.end_datetime,
    description=db_body.description,
    external_source_id=db_body.external_source_id,
)

minimal_ingestion_session = ingestion_models.Session(
    session_datetime=db_session.session_datetime, video_uri=db_session.video_uri
)
full_ingestion_session = ingestion_models.Session(
    session_datetime=db_session.session_datetime,
    video_uri=db_session.video_uri,
    caption_uri=db_session.caption_uri,
    external_source_id=db_session.external_source_id,
)

minimal_ingestion_event = ingestion_models.EventIngestionModel(
    body=minimal_ingestion_body, sessions=[minimal_ingestion_session]
)


def test_create_cdp_event_gather_flow() -> None:
    with mock.patch("fireo.connection") as mock_connector:
        mock_connector.return_value = None
        flow = pipeline.create_cdp_event_gather_flow(
            mock_get_events_func, "/fake/credentials/path"
        )
        assert isinstance(flow, Flow)


@pytest.mark.parametrize(
    "model, mock_return_value, expected",
    [
        (db_body, UniquenessValidation(True, []), db_body),
        (db_body, UniquenessValidation(False, [db_body_extra]), db_body_extra),
    ],
)
def test_upload_db_model(
    model: Model,
    mock_return_value: UniquenessValidation,
    expected: Model,
) -> None:
    with mock.patch(
        "cdp_backend.pipeline.cdp_event_gather_pipeline.get_model_uniqueness"
    ) as mock_uniqueness_validator:
        mock_uniqueness_validator.return_value = mock_return_value

        with mock.patch("fireo.models.Model.save") as mock_saver:
            mock_saver.return_value = None

            actual_uploaded_model = pipeline.upload_db_model.run(model)  # type: ignore

            assert expected == actual_uploaded_model


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


def mock_get_events_func() -> List[EventIngestionModel]:
    event = EXAMPLE_MINIMAL_EVENT
    event.sessions[0].session_datetime = datetime(2019, 4, 13)
    return [event]


def assert_ingestion_and_db_models_equal(
    ingestion_model: Any,
    expected_db_model: Model,
    actual_db_model: Model,
) -> None:
    fields = [attr for attr in dir(ingestion_model) if not attr.startswith("__")]

    for field in fields:
        ingestion_value = getattr(ingestion_model, field)

        # Minimal models may be missing some values
        # Some fields like reference fields don't match between ingestion and db models
        # Those are asserted in the more specific methods
        if ingestion_value and hasattr(expected_db_model, field):
            assert getattr(expected_db_model, field) == getattr(actual_db_model, field)
