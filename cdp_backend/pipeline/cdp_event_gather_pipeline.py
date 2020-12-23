#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
import logging
from typing import Callable, List

from cdp_backend.pipeline.ingestion_models import EventIngestionModel, Body, Session
import cdp_backend.database.models as db_models
from cdp_backend.database.validators import get_model_uniqueness

from prefect import Flow, task

import fireo

###############################################################################

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)4s: %(module)s:%(lineno)4s %(asctime)s] %(message)s",
)
log = logging.getLogger(__name__)

###############################################################################


def create_cdp_event_gather_flow(
    get_events_func: Callable,
    credentials_file: str,
) -> Flow:
    # Initialize fireo connection
    fireo.connection(from_file=credentials_file)

    # Create flow
    with Flow("CDP Event Gather Pipeline") as flow:
        events: List[EventIngestionModel] = get_events_func()

        for event in events:
            process_event(event)

    return flow


def process_event(event: EventIngestionModel) -> None:
    # TODO create/get transcript
    # TODO create/get audio (happens as part of transcript process)

    # Upload converted ingestion models to databae
    upload_to_database(event)


def upload_to_database(event: EventIngestionModel) -> None:
    # Upload calls for minimal event
    body_ref = upload_body(event.body)

    # TODO add upload calls for non-minimal event

    event_ref = upload_event(event, body_ref)

    for session in event.sessions:
        upload_session(session, event_ref)


@task
def upload_event(
    event: EventIngestionModel, body_ref: db_models.Body
) -> db_models.Event:
    db_event = db_models.Event()

    # Required fields
    db_event.body_ref = body_ref

    # Assume that session is same day as event
    db_event.event_datetime = event.sessions[0].session_datetime

    # TODO add optional fields

    uniqueness_validation = get_model_uniqueness(db_event)
    if uniqueness_validation.is_unique:
        db_event.save()
        log.info(f"Saved new Event with document id={db_event.id}.")
    else:
        return uniqueness_validation.conflicting_models[0]

    return db_event


@task
def upload_body(body: Body) -> db_models.Body:
    db_body = db_models.Body()

    # Required fields
    db_body.name = body.name
    db_body.is_active = body.is_active
    if body.start_datetime is None:
        db_body.start_datetime = datetime.utcnow()
    else:
        db_body.start_datetime = body.start_datetime

    # Optional fields
    if body.end_datetime:
        db_body.end_datetime = body.end_datetime

    if body.description:
        db_body.description = body.description

    if body.external_source_id:
        db_body.external_source_id = body.external_source_id

    uniqueness_validation = get_model_uniqueness(db_body)
    if uniqueness_validation.is_unique:
        db_body.save()
        log.info(f"Saved new Body with document id={db_body.id}.")
    else:
        return uniqueness_validation.conflicting_models[0]

    return db_body


@task
def upload_session(session: Session, event_ref: db_models.Event) -> db_models.Session:
    db_session = db_models.Session()

    # Required fields
    db_session.event_ref = event_ref
    db_session.session_datetime = session.session_datetime
    db_session.video_uri = session.video_uri

    if session.session_index:
        db_session.session_index = session.session_index
    else:
        # Is this how we want to handle when session_index isn't provided?
        db_session.session_index = 0

    # Optional fields
    if session.caption_uri:
        db_session.caption_uri = session.caption_uri

    if session.external_source_id:
        db_session.external_source_id = session.external_source_id

    uniqueness_validation = get_model_uniqueness(db_session)
    if uniqueness_validation.is_unique:
        db_session.save()
        log.info(f"Saved new Session with document id={db_session.id}.")
    else:
        return uniqueness_validation.conflicting_models[0]

    return db_session
