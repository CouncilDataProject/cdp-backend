#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
from typing import Callable, List

import pytest
from prefect import Flow

from cdp_backend.database import models as db_models
from cdp_backend.pipeline import event_gather_pipeline as pipeline
from cdp_backend.pipeline.ingestion_models import (
    EXAMPLE_MINIMAL_EVENT,
    Body,
    EventIngestionModel,
    Session,
)
from cdp_backend.pipeline.mock_get_events import get_events as rand_get_events

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


def min_get_events() -> List[EventIngestionModel]:
    event = EXAMPLE_MINIMAL_EVENT
    event.sessions[0].session_datetime = datetime(2019, 4, 13)
    return [event]


@pytest.mark.parametrize("func", [min_get_events, rand_get_events])
def test_create_event_gather_flow(func: Callable) -> None:
    flow = pipeline.create_event_gather_flow(
        get_events_func=func,
        credentials_file="/fake/credentials/path",
    )
    assert isinstance(flow, Flow)


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
