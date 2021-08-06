#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from typing import Any, Optional

import fireo
from fireo.models import Model
from google.cloud.firestore_v1.transaction import Transaction

from ..database import exceptions
from ..database import models as db_models
from ..database.validators import get_model_uniqueness
from ..pipeline import ingestion_models, transcript_model
from ..pipeline.ingestion_models import IngestionModel

###############################################################################

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
        db_model = db_model.update(db_model.key, transaction=transaction)

    return db_model


def upload_db_model(
    db_model: Model,
    credentials_file: str,
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
    credentials_file: str
        Path to Google Service Account Credentials JSON file.
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
    # Init transaction and auth
    fireo.connection(from_file=credentials_file)

    uniqueness_validation = get_model_uniqueness(db_model)
    if uniqueness_validation.is_unique:
        db_model = db_model.save(transaction=transaction)
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
        # Exist okay was selected, update existing model and return
        #
        # Previously this simply returned the found conflicting model
        # But a prime example of where we should update is in the Role Model
        # Where we can find an existing model based off primary keys
        # But if we were ingesting a model that had an end_datetime
        # and the current database model didn't have an end_datetime
        # we wouldn't have updated the database model with the newly provided
        # end_datetime
        db_model = db_model.update(
            key=uniqueness_validation.conflicting_models[0].key,
            transaction=transaction,
        )

    else:
        raise exceptions.UniquenessError(
            model=db_model, conflicting_results=uniqueness_validation.conflicting_models
        )

    return db_model


def _strip_field(field: Optional[str]) -> Optional[str]:
    if isinstance(field, str):
        return field.strip()

    return field


def _ensure_string_or_optional(field: Optional[Any]) -> Optional[str]:
    if field is not None:
        return str(field)

    return None


def create_body(
    body: ingestion_models.Body,
    start_datetime: datetime,
) -> db_models.Body:
    db_body = db_models.Body()

    # Required fields
    db_body.name = _strip_field(body.name)
    db_body.is_active = body.is_active
    db_body.start_datetime = start_datetime

    # Optional fields
    db_body.end_datetime = body.end_datetime
    db_body.description = _strip_field(body.description)
    db_body.external_source_id = _ensure_string_or_optional(body.external_source_id)

    return db_body


def create_event(
    body_ref: db_models.Body,
    event_datetime: datetime,
    static_thumbnail_ref: Optional[db_models.File] = None,
    hover_thumbnail_ref: Optional[db_models.File] = None,
    agenda_uri: Optional[str] = None,
    minutes_uri: Optional[str] = None,
    external_source_id: Optional[str] = None,
) -> db_models.Event:
    db_event = db_models.Event()

    # Required fields
    db_event.body_ref = body_ref
    db_event.event_datetime = event_datetime

    # Optional fields
    db_event.static_thumbnail_ref = static_thumbnail_ref
    db_event.hover_thumbnail_ref = hover_thumbnail_ref
    db_event.agenda_uri = _strip_field(agenda_uri)
    db_event.minutes_uri = _strip_field(minutes_uri)
    db_event.external_source_id = _ensure_string_or_optional(external_source_id)

    return db_event


def create_session(
    session: ingestion_models.Session, event_ref: db_models.Event
) -> db_models.Session:
    db_session = db_models.Session()

    # Required fields
    db_session.event_ref = event_ref
    db_session.session_datetime = session.session_datetime
    db_session.video_uri = session.video_uri
    db_session.session_index = session.session_index

    # Optional fields
    db_session.caption_uri = session.caption_uri
    db_session.external_source_id = _ensure_string_or_optional(
        session.external_source_id
    )

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


def create_matter(
    matter: ingestion_models.Matter,
) -> db_models.Matter:
    db_matter = db_models.Matter()

    db_matter.name = _strip_field(matter.name)
    db_matter.matter_type = _strip_field(matter.matter_type)
    db_matter.title = _strip_field(matter.title)
    db_matter.external_source_id = _ensure_string_or_optional(matter.external_source_id)

    return db_matter


def create_matter_status(
    matter_ref: db_models.Matter,
    status: str,
    update_datetime: datetime,
    event_minutes_item_ref: Optional[db_models.EventMinutesItem] = None,
    external_source_id: Optional[str] = None,
) -> db_models.Matter:
    db_matter_status = db_models.MatterStatus()

    db_matter_status.matter_ref = matter_ref
    db_matter_status.event_minutes_item_ref = event_minutes_item_ref
    db_matter_status.status = _strip_field(status)
    db_matter_status.update_datetime = update_datetime
    db_matter_status.external_source_id = _ensure_string_or_optional(external_source_id)

    return db_matter_status


def create_matter_file(
    matter_ref: db_models.Matter,
    supporting_file: ingestion_models.SupportingFile,
) -> db_models.MatterFile:
    db_matter_file = db_models.MatterFile()

    db_matter_file.matter_ref = matter_ref
    db_matter_file.name = _strip_field(supporting_file.name)
    db_matter_file.uri = _strip_field(supporting_file.uri)
    db_matter_file.external_source_id = _ensure_string_or_optional(
        supporting_file.external_source_id
    )

    return db_matter_file


def create_minimal_person(
    person: ingestion_models.Person,
) -> db_models.Person:
    db_person = db_models.Person()

    db_person.name = _strip_field(person.name)
    db_person.is_active = person.is_active
    db_person.router_string = db_models.Person.generate_router_string(
        _strip_field(person.name)  # type: ignore
    )

    return db_person


def create_matter_sponsor(
    matter_ref: db_models.Matter,
    person_ref: db_models.Person,
    external_source_id: Optional[str] = None,
) -> db_models.MatterSponsor:
    db_matter_sponsor = db_models.MatterSponsor()

    db_matter_sponsor.matter_ref = matter_ref
    db_matter_sponsor.person_ref = person_ref
    db_matter_sponsor.external_source_id = _ensure_string_or_optional(
        external_source_id
    )

    return db_matter_sponsor


def create_person(
    person: ingestion_models.Person,
    picture_ref: Optional[db_models.File] = None,
) -> db_models.Person:
    # Get minimal
    db_person = create_minimal_person(person=person)

    # Optional
    db_person.router_string = _strip_field(person.router_string)
    db_person.email = _strip_field(person.email)
    db_person.phone = _strip_field(person.phone)
    db_person.website = _strip_field(person.website)
    db_person.picture_ref = picture_ref
    db_person.external_source_id = _ensure_string_or_optional(person.external_source_id)

    return db_person


def create_seat(
    seat: ingestion_models.Seat,
    image_ref: Optional[db_models.File],
) -> db_models.Seat:
    db_seat = db_models.Seat()

    db_seat.name = _strip_field(seat.name)
    db_seat.electoral_area = _strip_field(seat.electoral_area)
    db_seat.electoral_type = _strip_field(seat.electoral_type)
    db_seat.image_ref = image_ref
    db_seat.external_source_id = _ensure_string_or_optional(seat.external_source_id)

    return db_seat


def create_role(
    role: ingestion_models.Role,
    person_ref: db_models.Person,
    seat_ref: db_models.Seat,
    start_datetime: datetime,
    body_ref: Optional[db_models.Body] = None,
) -> db_models.Role:
    db_role = db_models.Role()

    # Required
    db_role.title = _strip_field(role.title)
    db_role.person_ref = person_ref
    db_role.seat_ref = seat_ref
    db_role.start_datetime = start_datetime

    # Optional
    db_role.body_ref = body_ref
    db_role.end_datetime = role.end_datetime
    db_role.external_source_id = _ensure_string_or_optional(role.external_source_id)

    return db_role


def create_minutes_item(
    minutes_item: ingestion_models.MinutesItem,
    matter_ref: Optional[db_models.Matter] = None,
) -> db_models.MinutesItem:
    db_minutes_item = db_models.MinutesItem()

    db_minutes_item.name = _strip_field(minutes_item.name)
    db_minutes_item.description = _strip_field(minutes_item.description)
    db_minutes_item.matter_ref = matter_ref
    db_minutes_item.external_source_id = _ensure_string_or_optional(
        minutes_item.external_source_id
    )

    return db_minutes_item


def create_minimal_event_minutes_item(
    event_ref: db_models.Event,
    minutes_item_ref: db_models.MinutesItem,
    index: int,
) -> db_models.EventMinutesItem:
    db_event_minutes_item = db_models.EventMinutesItem()

    db_event_minutes_item.event_ref = event_ref
    db_event_minutes_item.minutes_item_ref = minutes_item_ref
    db_event_minutes_item.index = index

    return db_event_minutes_item


def create_event_minutes_item(
    event_minutes_item: ingestion_models.EventMinutesItem,
    event_ref: db_models.Event,
    minutes_item_ref: db_models.MinutesItem,
    index: int,
) -> db_models.EventMinutesItem:
    db_event_minutes_item = create_minimal_event_minutes_item(
        event_ref=event_ref,
        minutes_item_ref=minutes_item_ref,
        index=index,
    )

    db_event_minutes_item.decision = event_minutes_item.decision

    return db_event_minutes_item


def create_event_minutes_item_file(
    event_minutes_item_ref: db_models.EventMinutesItem,
    supporting_file: ingestion_models.SupportingFile,
) -> db_models.EventMinutesItemFile:
    db_event_minutes_item_file = db_models.EventMinutesItemFile()

    db_event_minutes_item_file.event_minutes_item_ref = event_minutes_item_ref
    db_event_minutes_item_file.name = _strip_field(supporting_file.name)
    db_event_minutes_item_file.uri = _strip_field(supporting_file.uri)
    db_event_minutes_item_file.external_source_id = _ensure_string_or_optional(
        supporting_file.external_source_id
    )

    return db_event_minutes_item_file


def create_vote(
    matter_ref: db_models.Matter,
    event_ref: db_models.Event,
    event_minutes_item_ref: db_models.EventMinutesItem,
    person_ref: db_models.Person,
    decision: str,
    in_majority: Optional[bool],
    external_source_id: Optional[str] = None,
) -> db_models.Vote:
    db_vote = db_models.Vote()

    db_vote.matter_ref = matter_ref
    db_vote.event_ref = event_ref
    db_vote.event_minutes_item_ref = event_minutes_item_ref
    db_vote.person_ref = person_ref
    db_vote.decision = _strip_field(decision)
    db_vote.in_majority = in_majority
    db_vote.external_source_id = _ensure_string_or_optional(external_source_id)

    return db_vote
