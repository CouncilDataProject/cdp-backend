#!/usr/bin/env python
# -*- coding: utf-8 -*-

import hashlib
import logging
from typing import Any, Callable, List

from prefect import Flow, case, task

from ..database import functions as db_functions
from ..database import models as db_models
from ..file_store import functions as fs_functions
from ..sr_models import GoogleCloudSRModel, sr_functions
from ..utils import file_utils as file_util_functions
from .ingestion_models import EventIngestionModel

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
    bucket: str,
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
    bucket: str
        Name of the GCS bucket to upload files to.

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
                db_functions.create_body_from_ingestion_model(event.body),
                event.body,
                creds_file=credentials_file,
            )

            # TODO add upload calls for non-minimal event

            event_ref = db_functions.upload_db_model_task(
                db_functions.create_event_from_ingestion_model(event, body_ref),
                event,
                creds_file=credentials_file,
            )

            for session in event.sessions:
                # Create db session
                session_ref = db_functions.upload_db_model_task(
                    db_functions.create_session_from_ingestion_model(
                        session, event_ref
                    ),
                    session,
                    creds_file=credentials_file,
                )

                # Create unique key for video uri
                key = hashlib.sha256(session.video_uri.encode("utf8")).hexdigest()

                # create/get audio (happens as part of transcript process)
                audio_uri = create_audio_and_transcript(
                    key,
                    session.video_uri,
                    bucket,
                    credentials_file,
                    session_ref,  # type: ignore
                )

                # Create transcript
                create_transcript(
                    audio_uri,  # type: ignore
                    session_ref,  # type: ignore
                    bucket,
                    credentials_file,
                )

    return flow


def create_audio_and_transcript(
    key: str,
    video_uri: str,
    bucket: str,
    credentials_file: str,
    session_ref: db_models.Session,
) -> str:
    """
    Creates an audio file from a video uri and uploads it to the filestore and db.

    Parameters
    ----------
    key: str
        The unique key made from a hash value of the video uri.
    bucket: str
        Name of the GCS bucket to upload files to.
    credentials_file: str
        Path to Google Service Account Credentials JSON file.

    Returns
    -------
    audio_uri: str
        The uri of the created audio file in the file store.
    """

    tmp_audio_filepath = f"{key}_audio.wav"
    audio_uri = fs_functions.get_file_uri_task(
        bucket=bucket, filename=tmp_audio_filepath, credentials_file=credentials_file
    )

    # Check if audio_uri is None or not
    exists = task_result_exists(audio_uri)

    # Create transcript with existing audio_uri
    with case(exists, True):  # type: ignore
        transcript = create_transcript(
            audio_uri, session_ref, bucket, credentials_file  # type: ignore
        )  # type: ignore

    # If no existing audio uri
    with case(exists, False):  # type: ignore
        # Store the video in temporary file
        filename = video_uri.split("/")[-1]
        if "." in filename:
            suffix = filename.split(".")[-1]
        else:
            suffix = ""

        tmp_video_filename = f"tmp_{key}_video.{suffix}"
        tmp_video_filepath = file_util_functions.external_resource_copy_task(
            uri=video_uri, dst=tmp_video_filename, overwrite=True
        )

        # Split and store the audio in temporary file prior to upload
        (
            tmp_audio_filepath,
            tmp_audio_log_out_filepath,
            tmp_audio_log_err_filepath,
        ) = file_util_functions.split_audio_task(
            video_read_path=tmp_video_filepath,
            audio_save_path=tmp_audio_filepath,
            overwrite=True,
        )

        # Store audio and logs
        audio_uri = fs_functions.upload_file_task(
            credentials_file=credentials_file,
            bucket=bucket,
            filepath=tmp_audio_filepath,
        )
        audio_log_out_uri = fs_functions.upload_file_task(
            credentials_file=credentials_file,
            bucket=bucket,
            filepath=tmp_audio_log_out_filepath,
        )
        audio_log_err_uri = fs_functions.upload_file_task(
            credentials_file=credentials_file,
            bucket=bucket,
            filepath=tmp_audio_log_err_filepath,
        )

        # Create database models for audio files
        audio_file_db_model = db_functions.create_file(
            name=fs_functions.create_filename_from_filepath(tmp_audio_filepath),
            uri=audio_uri,
        )
        audio_out_file_db_model = db_functions.create_file(
            name=fs_functions.create_filename_from_filepath(tmp_audio_log_out_filepath),
            uri=audio_log_out_uri,
        )
        audio_err_file_db_model = db_functions.create_file(
            name=fs_functions.create_filename_from_filepath(tmp_audio_log_err_filepath),
            uri=audio_log_err_uri,
        )

        # TODO: Either add ingestion model to upload_db_model_task call
        # or support db model updates without ingestion model

        # Upload files to database
        uploaded_file_db_model = db_functions.upload_db_model_task(
            audio_file_db_model, None, credentials_file
        )
        uploaded_out_db_model = db_functions.upload_db_model_task(
            audio_out_file_db_model, None, credentials_file
        )
        uploaded_err_db_model = db_functions.upload_db_model_task(
            audio_err_file_db_model, None, credentials_file
        )

        # Remove tmp files after their final dependent tasks are finished
        fs_functions.remove_local_file_task(
            tmp_video_filepath, upstream_tasks=[tmp_audio_filepath]
        )
        fs_functions.remove_local_file_task(
            tmp_audio_filepath, upstream_tasks=[uploaded_file_db_model]
        )
        fs_functions.remove_local_file_task(
            tmp_audio_log_out_filepath, upstream_tasks=[uploaded_out_db_model]
        )
        fs_functions.remove_local_file_task(
            tmp_audio_log_err_filepath, upstream_tasks=[uploaded_err_db_model]
        )

        # Create transcript
        transcript = create_transcript(
            audio_uri, session_ref, bucket, credentials_file  # type: ignore
        )  # type: ignore

    return (audio_uri, transcript)  # type: ignore


def create_transcript(
    audio_uri: str, session_ref: db_models.Session, bucket: str, credentials_file: str
) -> db_models.Transcript:
    """
    Creates a transcript from an audio uri and uploads it to the filestore and db.

    Parameters
    ----------
    audio_uri: str
        The uri of the audio file to transcribe.
        Should be in form of 'gs://...'
    bucket: str
        Name of the GCS bucket to upload files to.
    credentials_file: str
        Path to Google Service Account Credentials JSON file.

    Returns
    -------
    transcript_db_ref: str
        The uri of the created audio file in the file store.
    """

    # Initialize SRModel
    sr_model = GoogleCloudSRModel(credentials_file)

    # Create Transcript with SRModel
    transcript = sr_functions.transcribe_task(sr_model=sr_model, file_uri=audio_uri)

    # Save transcript locally as JSON file
    save_path = file_util_functions.save_dataclass_as_json_file(
        data=transcript, save_path=audio_uri + "_transcript"
    )

    # Upload transcript as file
    transcript_file_uri = fs_functions.upload_file_task(
        credentials_file=credentials_file,
        bucket=bucket,
        filepath=save_path,
        remove_local=True,
    )

    # Create filename for db model of file for transcript
    filename = file_util_functions.create_filename_from_file_uri(transcript_file_uri)

    # Create file db model for transcript
    db_file_model = db_functions.create_file(name=filename, uri=transcript_file_uri)

    # Upload file db model for transcript
    db_file_ref = db_functions.upload_db_model_task(
        db_model=db_file_model, ingestion_model=None, creds_file=credentials_file
    )

    # Create transcript db model
    db_transcript_model = db_functions.create_transcript(
        transcript_file=db_file_ref, session=session_ref, transcript=transcript
    )

    # Upload transcript db model
    db_transcript_ref = db_functions.upload_db_model_task(
        db_model=db_transcript_model, ingestion_model=None, creds_file=credentials_file
    )

    return db_transcript_ref  # type: ignore


@task
def task_result_exists(result: Any) -> bool:
    return result is not None
