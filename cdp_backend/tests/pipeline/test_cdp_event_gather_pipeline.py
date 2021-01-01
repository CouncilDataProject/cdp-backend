#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ...database import models as db_models
from ...database import exceptions
from ...database.validators import UniquenessValidation
from ...pipeline import cdp_event_gather_pipeline as pipeline
from ...pipeline import ingestion_models
from ...pipeline.ingestion_models import (
    Body,
    EventIngestionModel,
    EXAMPLE_MINIMAL_EVENT,
    Session,
)

import copy
from datetime import datetime
from fireo.models import Model
from typing import Any, List
from prefect import Flow
from unittest import mock
import pytest


db_body = db_models.Body.Example()
db_body.description = "description"
db_body.end_datetime = datetime(2039, 1, 1)
db_body.external_source_id = "external_source_id"
db_body_extra = db_models.Body.Example()

updated_desc = "updated description"
db_body_updated = copy.deepcopy(db_body)
db_body_updated.description = updated_desc

db_event = db_models.Event.Example()
db_event.body_ref = db_body

db_session = db_models.Session.Example()
db_session.event_ref = db_event
db_session.session_index = 1
db_session.caption_uri = "caption_uri"

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
updated_ingestion_body = ingestion_models.Body(
    name=db_body_updated.name,
    is_active=db_body_updated.is_active,
    description=updated_desc,
)

minimal_ingestion_session = ingestion_models.Session(
    session_datetime=db_session.session_datetime, video_uri=db_session.video_uri
)
full_ingestion_session = ingestion_models.Session(
    session_datetime=db_session.session_datetime,
    video_uri=db_session.video_uri,
    caption_uri=db_session.caption_uri,
    external_source_id=db_session.external_source_id,
    session_index=db_session.session_index,
)

minimal_ingestion_event = ingestion_models.EventIngestionModel(
    body=minimal_ingestion_body, sessions=[minimal_ingestion_session]
)


def mock_get_events_func() -> List[EventIngestionModel]:
    event = EXAMPLE_MINIMAL_EVENT
    event.sessions[0].session_datetime = datetime(2019, 4, 13)
    return [event]


def assert_db_models_equality(
    actual_db_model: Model, expected_db_model: Model, equality_check: bool
) -> None:
    fields = [
        attr
        for attr in dir(expected_db_model)
        if not attr.startswith("_") and attr not in dir(Model)
    ]
    are_not_equal = False

    for field in fields:
        expected_value = getattr(expected_db_model, field)

        if expected_value and hasattr(actual_db_model, field):
            if equality_check:
                assert getattr(expected_db_model, field) == getattr(
                    actual_db_model, field
                )
            else:
                # Switch flag if any differences are found
                are_not_equal = are_not_equal or (
                    getattr(expected_db_model, field) != getattr(actual_db_model, field)
                )

    if not equality_check:
        assert are_not_equal == True


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


def test_create_cdp_event_gather_flow() -> None:
    with mock.patch("fireo.connection") as mock_connector:
        mock_connector.return_value = None
        flow = pipeline.create_cdp_event_gather_flow(
            mock_get_events_func, "/fake/credentials/path"
        )
        assert isinstance(flow, Flow)


@pytest.mark.parametrize(
    "db_model, ingestion_model, db_key, mock_return_value, expected",
    [
        (
            copy.deepcopy(db_body),
            updated_ingestion_body,
            db_body.key,
            None,
            db_body_updated,
        ),
    ],
)
def test_update_db_model(
    db_model: Model,
    ingestion_model: Any,
    db_key: str,
    mock_return_value: Model,
    expected: Model,
) -> None:
    with mock.patch("fireo.models.Model.update") as mock_updater:
        mock_updater.return_value = None

        # Check that models is different pre-update
        assert_db_models_equality(expected, db_model, False)

        actual_updated_model = pipeline.update_db_model(
            db_model, ingestion_model, db_key
        )

        # Check that model is correctly updated
        assert_db_models_equality(expected, actual_updated_model, True)


@pytest.mark.parametrize(
    "db_model, ingestion_model, mock_return_value, expected",
    [
        (db_body, full_ingestion_body, UniquenessValidation(True, []), db_body),
        (
            db_body,
            full_ingestion_body,
            UniquenessValidation(False, [db_body_extra]),
            db_body_extra,
        ),
        pytest.param(
            db_body,
            full_ingestion_body,
            UniquenessValidation(False, [db_body, db_body_extra]),
            None,
            marks=pytest.mark.raises(exception=exceptions.UniquenessError),
        )
    ],
)
def test_upload_db_model(
    db_model: Model,
    ingestion_model: Any,
    mock_return_value: UniquenessValidation,
    expected: Model,
) -> None:
    with mock.patch(
        "cdp_backend.pipeline.cdp_event_gather_pipeline.get_model_uniqueness"
    ) as mock_uniqueness_validator:
        mock_uniqueness_validator.return_value = mock_return_value

        with mock.patch("fireo.models.Model.save") as mock_saver:
            mock_saver.return_value = None

            with mock.patch(
                "cdp_backend.pipeline.cdp_event_gather_pipeline.update_db_model"
            ) as mock_updater:
                mock_updater.return_value = mock_return_value.conflicting_models[0] if mock_return_value.conflicting_models else None

                actual_uploaded_model = pipeline.upload_db_model.run(db_model, ingestion_model)  # type: ignore

                assert_db_models_equality(expected, actual_uploaded_model, True)


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
