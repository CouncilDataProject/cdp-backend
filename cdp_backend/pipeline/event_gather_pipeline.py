#!/usr/bin/env python
# -*- coding: utf-8 -*-

import hashlib
import logging
from typing import Callable, List

from prefect import Flow, case

from ..database import functions as db_functions
from ..file_store import functions as fs_functions
from ..sr_models import GoogleCloudSRModel
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

        sr_model = GoogleCloudSRModel(credentials_file)
        sr_model.transcribe("gs://stg-cdp-seattle-a910f.appspot.com/short_audio.wav")

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
                # Create unique key for video uri
                key = hashlib.sha256(session.video_uri.encode("utf8")).hexdigest()

                # create/get audio (happens as part of transcript process)
                audio_uri = create_or_get_audio(key, session.video_uri, bucket, credentials_file)

                # Create transcript from audio file
                transcript = sr_model.transcribe(audio_uri)

                # TODO 
                # Create transcript save path with json 
                transcript_save_path = file_util_functions.save_json_as_file(transcript.tojson(), audio_uri + "_transcript")

                
               transcript_file_uri = fs_functions.upload_file_task(
                       credentials_file=credentials_file,
                        bucket=bucket,
                        filepath=transcript_save_path,
                        save_name=None,
                        remove_local=True) 
                # call db_functions.create_transcript on that file and transcript

                db_functions.upload_db_model_task(
                    db_functions.create_session_from_ingestion_model(
                        session, event_ref
                    ),
                    session,
                    creds_file=credentials_file,
                )

    return flow


def create_or_get_audio(
    key: str, video_uri: str, bucket: str, credentials_file: str
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

    # If no existing audio uri
    with case(audio_uri, None):  # type: ignore
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
        (
            tmp_audio_filepath,
            tmp_audio_log_out_filepath,
            tmp_audio_log_err_filepath,
        ) = file_util_functions.split_audio_task(
            video_read_path=tmp_video_filepath,
            audio_save_path=tmp_audio_filepath,
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

    return audio_uri  # type: ignore
