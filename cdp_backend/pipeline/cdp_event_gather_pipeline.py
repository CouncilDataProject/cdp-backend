#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from typing import Any, Callable, List

import fireo
from fireo.models import Model
from prefect import Flow, task

from ..database import exceptions
from ..database import models as db_models
from ..database.validators import get_model_uniqueness
from .ingestion_models import Body, EventIngestionModel, Session

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
    # Create flow
    with Flow("CDP Event Gather Pipeline") as flow:
        events: List[EventIngestionModel] = get_events_func()

        for event in events:
            # TODO create/get transcript
            # TODO create/get audio (happens as part of transcript process)

            # Upload calls for minimal event
            body_ref = upload_db_model(
                create_body_from_ingestion_model(event.body),
                event.body,
                creds_file=credentials_file,
            )

            # TODO add upload calls for non-minimal event

            event_ref = upload_db_model(
                create_event_from_ingestion_model(event, body_ref),
                event,
                creds_file=credentials_file,
            )

            for session in event.sessions:
                upload_db_model(
                    create_session_from_ingestion_model(session, event_ref),
                    session,
                    creds_file=credentials_file,
                )

    return flow


def update_db_model(db_model: Model, ingestion_model: Any, db_key: str) -> Model:
    # Filter out base class attrs, unrelated class methods, primary keys
    non_primary_db_fields = [
        attr
        for attr in dir(db_model)
        if (
            not attr.startswith("_")
            and attr not in dir(Model)
            and attr not in db_model._PRIMARY_KEYS
        )
    ]

    needs_update = False
    for field in non_primary_db_fields:
        if hasattr(ingestion_model, field):
            db_val = getattr(db_model, field)
            ingestion_val = getattr(ingestion_model, field)

            # If values are different, use the ingestion value
            # Make sure we don't overwrite with empty values
            if db_val != ingestion_val and ingestion_val is not None:
                setattr(db_model, field, ingestion_val)
                needs_update = True
                log.info(f"Updating {db_key} {field} from {db_val} to {ingestion_val}.")

    # Avoid unnecessary db interactions
    if needs_update:
        db_model.update(db_key)

    return db_model


@task
def upload_db_model(db_model: Model, ingestion_model: Any, creds_file: str) -> Model:
    # Initialize fireo connection
    fireo.connection(from_file=creds_file)

    uniqueness_validation = get_model_uniqueness(db_model)
    if uniqueness_validation.is_unique:
        db_model.save()
        log.info(
            f"Saved new {db_model.__class__.__name__} with document id={db_model.id}."
        )
    elif len(uniqueness_validation.conflicting_models) == 1:
        updated_db_model = update_db_model(
            uniqueness_validation.conflicting_models[0],
            ingestion_model,
            uniqueness_validation.conflicting_models[0].key,
        )

        return updated_db_model
    else:
        raise exceptions.UniquenessError(
            model=db_model, conflicting_results=uniqueness_validation.conflicting_models
        )

    return db_model


@task
def create_body_from_ingestion_model(body: Body) -> db_models.Body:
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

    return db_body


@task
def create_event_from_ingestion_model(
    event: EventIngestionModel, body_ref: db_models.Body
) -> db_models.Event:
    db_event = db_models.Event()

    # Required fields
    db_event.body_ref = body_ref

    # Assume event datetime is the date of earliest session
    db_event.event_datetime = min(
        [session.session_datetime for session in event.sessions]
    )

    # TODO add optional fields

    return db_event


@task
def create_session_from_ingestion_model(
    session: Session, event_ref: db_models.Event
) -> db_models.Session:
    db_session = db_models.Session()

    # Required fields
    db_session.event_ref = event_ref
    db_session.session_datetime = session.session_datetime
    db_session.video_uri = session.video_uri
    db_session.session_index = session.session_index

    # Optional fields
    if session.caption_uri:
        db_session.caption_uri = session.caption_uri

    if session.external_source_id:
        db_session.external_source_id = session.external_source_id

    return db_session
