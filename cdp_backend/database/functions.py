#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from typing import Optional

from fireo.models import Model
from google.cloud.firestore_v1.transaction import Transaction

from ..database import exceptions
from ..database import models as db_models
from ..database.validators import get_model_uniqueness
from ..pipeline import ingestion_models, transcript_model
from ..pipeline.ingestion_models import IngestionModel

###############################################################################

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)4s: %(module)s:%(lineno)4s %(asctime)s] %(message)s",
)
log = logging.getLogger(__name__)

###############################################################################


def update_db_model(
    db_model: Model,
    ingestion_model: IngestionModel,
    transaction: Optional[Transaction] = None,
) -> Model:
    """
    Compare an existing database model to an ingestion model and if the non-primary
    fields are different, update the database model.

    Parameters
    ----------
    db_model: Model
        The existing database model to compare new data against.
    ingestion_model: IngestionModel
        The data to compare against and potentially use for updating.
    transaction: Optional[Transaction]
        The transaction to write this model during.

    Returns
    -------
    db_model: Model
        The updated database model.
    """
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
                log.debug(
                    f"Updating {db_model.key} {field} from {db_val} to {ingestion_val}."
                )

    # Avoid unnecessary db interactions
    if needs_update:
        db_model.update(db_model.key, transaction=transaction)

    return db_model


def upload_db_model(
    db_model: Model,
    transaction: Optional[Transaction] = None,
    ingestion_model: Optional[IngestionModel] = None,
    exist_ok: bool = False,
) -> Model:
    """
    Upload or update an existing database model.

    Parameters
    ----------
    db_model: Model
        The database model to upload.
    transaction: Optional[Transaction]
        The transaction to write this model during.
    ingestion_model: Optional[IngestionModel]
        The accompanying ingestion model in the case the model already exists and needs
        to be updated rather than inserted.
    exist_ok: bool
        If there is an existing database document found during upload, is it okay for
        it to exist and simply return.
        Default: False

    Returns
    -------
    db_model: Model
        The uploaded, or updated, database model.

    Raises
    ------
    exceptions.UniquenessError
        More than one (1) conflicting model was found in the database. This should
        never occur and indicates that something is wrong with the database.
    """
    uniqueness_validation = get_model_uniqueness(db_model)
    if uniqueness_validation.is_unique:
        db_model.save(transaction=transaction)
        log.debug(
            f"Saved new {db_model.__class__.__name__} with document id={db_model.id}."
        )
    elif (
        len(uniqueness_validation.conflicting_models) == 1
        and ingestion_model is not None
    ):
        updated_db_model = update_db_model(
            db_model=uniqueness_validation.conflicting_models[0],
            ingestion_model=ingestion_model,
            transaction=transaction,
        )

        return updated_db_model
    elif len(uniqueness_validation.conflicting_models) == 1 and exist_ok:
        return uniqueness_validation.conflicting_models[0]
    else:
        raise exceptions.UniquenessError(
            model=db_model, conflicting_results=uniqueness_validation.conflicting_models
        )

    return db_model


def create_body_from_ingestion_model(body: ingestion_models.Body) -> db_models.Body:
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


def create_event_from_ingestion_model(
    event: ingestion_models.EventIngestionModel, body_ref: db_models.Body
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


def create_session_from_ingestion_model(
    session: ingestion_models.Session, event_ref: db_models.Event
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


def create_file(uri: str) -> db_models.File:
    db_file = db_models.File()
    db_file.name = uri.split("/")[-1]
    db_file.uri = uri

    return db_file


def create_transcript(
    transcript_file_ref: db_models.File,
    session_ref: db_models.Session,
    transcript: transcript_model.Transcript,
) -> db_models.Transcript:
    db_transcript = db_models.Transcript()

    db_transcript.session_ref = session_ref
    db_transcript.file_ref = transcript_file_ref
    db_transcript.confidence = transcript.confidence
    db_transcript.created = datetime.fromisoformat(transcript.created_datetime)

    return db_transcript
