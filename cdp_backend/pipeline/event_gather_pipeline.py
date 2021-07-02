#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from typing import Callable, List, Tuple

from prefect import Flow, task

from ..database import functions as db_functions
from ..database import models as db_models
from ..file_store import functions as fs_functions
from ..utils import file_utils as file_util_functions
from .ingestion_models import EventIngestionModel, Session
from .transcript_model import Transcript

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
            # TODO add upload calls for non-minimal event
            for session in event.sessions:
                # TODO create/get transcript

                # Create db session
                # session_ref = db_functions.upload_db_model_task(
                #     db_functions.create_session_from_ingestion_model(
                #         session, event_ref
                #     ),
                #     session,
                #     creds_file=credentials_file,
                # )

                # Get or create audio
                audio_uri = get_video_and_split_audio(
                    video_uri=session.video_uri,
                    bucket=bucket,
                    credentials_file=credentials_file,
                )

                # Generate transcript
                transcript_uri = generate_transcript(
                    audio_uri=audio_uri,
                    session=session,
                    bucket=bucket,
                    credentials_file=credentials_file,
                )

                # Generate thumbnails
                (
                    static_thumbnail_uri,
                    hover_thumbnail_uri,
                ) = get_video_and_generate_thumbnails(
                    video_uri=session.video_uri,
                    bucket=bucket,
                    credentials_file=credentials_file,
                )

                # Store all processed and provided data
                store_processed_session(
                    session=session,
                    audio_uri=audio_uri,
                    transcript_uri=transcript_uri,
                    static_thumbnail_uri=static_thumbnail_uri,
                    hover_thumbnail_uri=hover_thumbnail_uri,
                )

    return flow


# get_video_and_split_audio(video_uri) -> str
# generate_transcript(audio_uri, closed_caption_uri) -> str:
#   case:
#       get_audio_and_generate_transcript(audio_uri) -> str
#       get_captions_and_generate_transcript(closed_caption_uri) -> str
# get_video_and_generate_thumbnails(video_uri) -> Tuple[str, str]
# store_processed_event_data(event, transcript, static_thumbnail, hover_thumbnail)


@task
def get_video_and_split_audio(
    video_uri: str, bucket: str, credentials_file: str
) -> str:
    """
    Download (or copy) a video file to temp storage, split's the audio, and uploads
    the audio to Google storage.

    Parameters
    ----------
    video_uri: str
        The URI to the video file to split audio from.
    bucket: str
        The name of the GCS bucket to upload the produced audio to.
    credentials_file: str
        Path to Google Service Account Credentials JSON file.

    Returns
    -------
    audio_uri: str
        The URI to the uploaded audio file.
    """
    # Get just the video filename from the full uri
    video_filename = video_uri.split("/")[-1]
    tmp_video_filepath = file_util_functions.resource_copy(
        uri=video_uri, dst=f"audio-splitting-{video_filename}"
    )

    # Hash the video contents
    key = file_util_functions.hash_file_contents(uri=tmp_video_filepath)

    # Check for existing audio
    tmp_audio_filepath = file_util_functions.join_strs_and_extension(
        parts=[key, "audio"], extension="wav"
    )
    audio_uri = fs_functions.get_file_uri(
        bucket=bucket, filename=tmp_audio_filepath, credentials_file=credentials_file
    )

    # If no pre-existing audio, split
    if audio_uri is None:
        # Split and store the audio in temporary file prior to upload
        (
            tmp_audio_filepath,
            tmp_audio_log_out_filepath,
            tmp_audio_log_err_filepath,
        ) = file_util_functions.split_audio(
            video_read_path=tmp_video_filepath,
            audio_save_path=tmp_audio_filepath,
            overwrite=True,
        )

        # Store audio and logs
        audio_uri = fs_functions.upload_file(
            credentials_file=credentials_file,
            bucket=bucket,
            filepath=tmp_audio_filepath,
        )
        audio_log_out_uri = fs_functions.upload_file(
            credentials_file=credentials_file,
            bucket=bucket,
            filepath=tmp_audio_log_out_filepath,
        )
        audio_log_err_uri = fs_functions.upload_file(
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
        for db_model in [
            audio_file_db_model,
            audio_out_file_db_model,
            audio_err_file_db_model,
        ]:
            db_functions.upload_db_model(
                db_model=db_model,
                ingestion_model=None,
                creds_file=credentials_file,
            )

        # Remove tmp files after their final dependent tasks are finished
        for local_path in [
            tmp_video_filepath,
            tmp_audio_filepath,
            tmp_audio_log_out_filepath,
            tmp_audio_log_err_filepath,
        ]:
            fs_functions.remove_local_file(local_path)

    return audio_uri


@task
def get_captions_and_generate_transcript(caption_uri: str) -> Transcript:
    """
    Download (or copy) a WebVTT closed caption file and convert to CDP Transcript model.

    Parameters
    ----------
    caption_uri: str
        The URI to the caption file to transform into the transcript.
    new_turn_pattern: str
        New speaker turn pattern to pass through to the WebVTT transformer.
    confidence: float
        Confidence to provide to the produced transcript.

    Returns
    -------
    transcript: Transcript
        The produced transcript.
    """
    pass


@task
def get_audio_and_generate_transcript(
    audio_uri: str,
    bucket: str,
    credentials_file: str,
) -> Transcript:
    pass


@task
def finalize_and_upload_transcript(
    transcript: Transcript,
    bucket: str,
    credentials_file: str,
    session: Session,
) -> str:
    pass


def generate_transcript(
    audio_uri: str,
    session: Session,
    bucket: str,
    credentials_file: str,
) -> str:
    """
    Route transcript generation to the correct processing.

    Parameters
    ----------
    audio_uri: str
        The URI to the audio file to generate a transcript from.
    session: Session
        The specific session details to be used in final transcript upload and archival.
        Additionally, if a closed caption URI is available on the session object,
        the transcript produced from this function will have been created using WebVTT
        caption transform rather than Google Speech-to-Text.
    bucket: str
        The name of the GCS bucket to upload the produced audio to.
    credentials_file: str
        Path to Google Service Account Credentials JSON file.

    Returns
    -------
    transcript_uri: The URI to the uploaded transcript file.
    """
    # If no captions, generate transcript with Google Speech-to-Text
    if session.caption_uri is None:
        transcript = get_audio_and_generate_transcript(
            audio_uri=audio_uri,
            bucket=bucket,
            credentials_file=credentials_file,
        )

    # Process captions
    else:
        transcript = get_captions_and_generate_transcript(
            caption_uri=session.caption_uri
        )

    # Add extra metadata and upload
    return finalize_and_upload_transcript(
        transcript=transcript,
        bucket=bucket,
        credentials_file=credentials_file,
        session=session,
    )


@task(nout=2)
def get_video_and_generate_thumbnails(
    video_uri: str, bucket: str, credentials_file: str
) -> Tuple[str, str]:
    pass


@task
def store_processed_session(
    session: Session,
    audio_uri: str,
    transcript_uri: str,
    static_thumbnail_uri: str,
    hover_thumbnail_uri: str,
) -> db_models.Session:
    pass
