#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from typing import Callable, List

from prefect import Flow, task

from ..database import functions as db_functions
from ..database import models as db_models
from ..file_store import functions as fs_functions
from ..utils import file_utils as file_util_functions
from .ingestion_models import Body, EventIngestionModel, Session

###############################################################################

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)4s: %(module)s:%(lineno)4s %(asctime)s] %(message)s",
)
log = logging.getLogger(__name__)

###############################################################################


def create_event_gather_flow(
    get_events_func: Callable,
    credentials_file: str,
) -> Flow:
    """
    Provided a function to gather new event information, create the Prefect Flow object
    to preview, run, or visualize.

    Parameters
    ----------
    get_events_func: Callable
        The event gather function written by the CDP instance maintainer(s).
    credentials_file: str
        Path to Google Service Account Credentials JSON file.

    Returns
    -------
    flow: Flow
        The constructed CDP Event Gather Pipeline as a Prefect Flow.
    """
    # Create flow
    with Flow("CDP Event Gather Pipeline") as flow:
        events: List[EventIngestionModel] = get_events_func()

        for event in events:

            # Upload calls for minimal event
            body_ref = db_functions.upload_db_model_task(
                create_body_from_ingestion_model(event.body),
                event.body,
                creds_file=credentials_file,
            )

            # TODO add upload calls for non-minimal event

            event_ref = db_functions.upload_db_model_task(
                create_event_from_ingestion_model(event, body_ref),
                event,
                creds_file=credentials_file,
            )

            for session in event.sessions:
                db_functions.upload_db_model_task(
                    create_session_from_ingestion_model(session, event_ref),
                    session,
                    creds_file=credentials_file,
                )

                # TODO create/get audio (happens as part of transcript process)

                key = hashlib.sha256(session.video_uri.encode("utf8")).hexdigest()

                # TODO create/get transcript
                # TODO pass bucket in via args
                bucket = 
                create_or_get_audio(key, session.video_uri, bucket, credentials_file)



    return flow


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


@task
def create_file(
    name: str,
    uri: str
) -> db_models.File:
    db_file = db_models.File()
    db_file.name = name
    db_file.uri = uri

    return db_file

def create_or_get_audio(
    key: str, 
    video_uri: str,
    bucket: str,
    credentials_file: str
) -> str:
    tmp_audio_filepath = f"{key}_audio.wav"
    try:
        audio_uri = fs_functions.get_file_uri(
            bucket=bucket, 
            filename=tmp_audio_filepath, 
            credentials_file=credentials_file
        )
    except FileNotFoundError:
        # Store the video in temporary file
        filename = video_uri.split("/")[-1]
        if "." in filename:
            suffix = filename.split(".")[-1]
        else:
            suffix = ""

        tmp_video_filename = f"tmp_{key}_video.{suffix}"
        tmp_video_filepath = file_util_functions.external_resource_copy_task(
            uri=video_uri, dst=tmp_video_filename
        )

        # Split and store the audio in temporary file prior to upload
        tmp_audio_filepath = file_util_functions.split_audio_task(
            video_read_path=tmp_video_filepath,
            audio_save_path=tmp_audio_filepath,
        )
        tmp_audio_log_out_filepath = tmp_audio_filepath.with_suffix(".out")
        tmp_audio_log_err_filepath = tmp_audio_filepath.with_suffix(".err")

        # Remove tmp video file
        fs_functions.remove_local_file(tmp_video_filepath)

        # Store audio and logs
        audio_uri = fs_functions.upload_file_task(
            credentials_file=credentials_file,
            bucket=bucket,
            filepath=tmp_audio_filepath
        )
        audio_log_out_uri = fs_functions.upload_file_task(
            credentials_file=credentials_file,
            bucket=bucket,
            filepath=tmp_audio_log_out_filepath
        )
        audio_log_err_uri = fs_functions.upload_file_task(
            credentials_file=credentials_file,
            bucket=bucket,
            filepath=tmp_audio_log_err_filepath
        )

        # TODO 
        # Store database records

    return audio_uri
