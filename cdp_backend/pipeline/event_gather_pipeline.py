#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from prefect import Flow, task

from ..database import functions as db_functions
from ..file_store import functions as fs_functions
from ..sr_models import GoogleCloudSRModel, WebVTTSRModel
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
    caption_new_speaker_turn_pattern: Optional[str] = None,
    caption_confidence: Optional[float] = None,
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
    caption_new_speaker_turn_pattern: Optional[str]
        Passthrough to sr_models.webvtt_sr_model.WebVTTSRModel.
    caption_confidence: Optional[float]
        Passthrough to sr_models.webvtt_sr_model.WebVTTSRModel.

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
                session_content_hash, audio_uri = get_video_and_split_audio(
                    video_uri=session.video_uri,
                    bucket=bucket,
                    credentials_file=credentials_file,
                )

                # Generate transcript
                transcript_uri = generate_transcript(
                    session_content_hash=session_content_hash,
                    audio_uri=audio_uri,
                    session=session,
                    bucket=bucket,
                    credentials_file=credentials_file,
                    caption_new_speaker_turn_pattern=caption_new_speaker_turn_pattern,
                    caption_confidence=caption_confidence,
                )

                # Generate thumbnails
                (
                    static_thumbnail_uri,
                    hover_thumbnail_uri,
                ) = get_video_and_generate_thumbnails(
                    session_content_hash=session_content_hash,
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


@task(nout=2)
def get_video_and_split_audio(
    video_uri: str, bucket: str, credentials_file: str
) -> Tuple[str, str]:
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
    session_content_hash: str
        The unique key (SHA256 hash of video content) for this session processing.
    audio_uri: str
        The URI to the uploaded audio file.
    """
    # Get just the video filename from the full uri
    video_filename = video_uri.split("/")[-1]
    tmp_video_filepath = file_util_functions.resource_copy(
        uri=video_uri,
        dst=f"audio-splitting-{video_filename}",
        overwrite=True,
    )

    # Hash the video contents
    session_content_hash = file_util_functions.hash_file_contents(
        uri=tmp_video_filepath
    )

    # Check for existing audio
    tmp_audio_filepath = file_util_functions.join_strs_and_extension(
        parts=[session_content_hash, "audio"],
        extension="wav",
        delimiter="-",
    )
    audio_uri = fs_functions.get_file_uri(
        bucket=bucket,
        filename=tmp_audio_filepath,
        credentials_file=credentials_file,
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
            name=Path(tmp_audio_filepath).name,
            uri=audio_uri,
        )
        audio_out_file_db_model = db_functions.create_file(
            name=Path(tmp_audio_log_out_filepath).name,
            uri=audio_log_out_uri,
        )
        audio_err_file_db_model = db_functions.create_file(
            name=Path(tmp_audio_log_err_filepath).name,
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

    return session_content_hash, audio_uri


@task
def use_speech_to_text_and_generate_transcript(
    audio_uri: str,
    credentials_file: str,
    phrases: Optional[List[str]] = None,
) -> Transcript:
    """
    Pass the audio URI through to Google Speech-to-Text.

    Parameters
    ----------
    audio_uri: str
        The URI to the audio path. The audio must already be stored in a GCS bucket.
    credentials_file: str
        Path to Google Service Account Credentials JSON file.
    phrases: Optional[List[str]]
        A list of strings to feed as targets to the model.

    Returns
    -------
    transcript: Transcript
        The generated Transcript object.
    """
    # Init model
    model = GoogleCloudSRModel(credentials_file=credentials_file)
    return model.transcribe(file_uri=audio_uri, phrases=phrases)


@task
def get_captions_and_generate_transcript(
    caption_uri: str,
    new_turn_pattern: Optional[str] = None,
    confidence: Optional[float] = None,
) -> Transcript:
    """
    Download (or copy) a WebVTT closed caption file and convert to CDP Transcript model.

    Parameters
    ----------
    caption_uri: str
        The URI to the caption file to transform into the transcript.
    new_turn_pattern: Optional[str]
        New speaker turn pattern to pass through to the WebVTT transformer.
    confidence: Optional[float]
        Confidence to provide to the produced transcript.

    Returns
    -------
    transcript: Transcript
        The produced transcript.
    """
    # If value provided, passthrough, otherwise ignore
    model_kwargs: Dict[str, Any] = {}
    if new_turn_pattern is not None:
        model_kwargs["new_turn_pattern"] = new_turn_pattern
    if confidence is not None:
        model_kwargs["confidence"] = confidence

    # Init model
    model = WebVTTSRModel(**model_kwargs)

    # Download or copy resource to local
    caption_filename = caption_uri.split("/")[-1]
    local_captions = file_util_functions.resource_copy(
        uri=caption_uri,
        dst=f"caption-transcribing-{caption_filename}",
        overwrite=True,
    )

    # Transcribe
    transcript = model.transcribe(file_uri=local_captions)

    # Remove temp file
    fs_functions.remove_local_file(local_captions)

    # Return generated transcript
    return transcript


@task
def finalize_and_archive_transcript(
    session_content_hash: str,
    transcript: Transcript,
    bucket: str,
    credentials_file: str,
    session: Session,
) -> str:
    """
    Finalizes metadata for a Transcript object, stores the transcript as JSON to object
    storage and finally adds transcript and file objects to database.

    Parameters
    ----------
    session_content_hash: str
        The unique key (SHA256 hash of video content) for this session processing.
    transcript: Transcript
        The transcript to finish processing and store.
    bucket: str
        The bucket to store the transcript to.
    credentials_file: str
        Path to Google Service Account Credentials JSON file.
    session: Session
        The event session to pull extra metadata from.

    Returns
    -------
    transcript_db_id: str
        The id of the stored transcript reference in the database.
    """
    # Add session datetime to transcript
    transcript.session_datetime = session.session_datetime.isoformat()

    # Dump to JSON
    transcript_save_name = f"{session_content_hash}-transcript.json"
    with open(transcript_save_name, "w") as open_resource:
        open_resource.write(transcript.to_json())  # type: ignore

    # Store to file store
    transcript_file_uri = fs_functions.upload_file(
        credentials_file=credentials_file,
        bucket=bucket,
        filepath=transcript_save_name,
    )

    # Store reference to file
    file_ref = db_functions.create_file(
        name=transcript_save_name,
        uri=transcript_file_uri,
    )

    # Store transcript reference
    # TODO:
    # Handle session / metadata upload
    # transcript_ref = db_functions.create_transcript(
    #     transcript_file=file_ref,
    #     session=session,
    #     transcript=transcript,
    # )

    # Remove local transcript
    fs_functions.remove_local_file(transcript_save_name)

    return file_ref


def generate_transcript(
    session_content_hash: str,
    audio_uri: str,
    session: Session,
    bucket: str,
    credentials_file: str,
    caption_new_speaker_turn_pattern: Optional[str] = None,
    caption_confidence: Optional[float] = None,
) -> str:
    """
    Route transcript generation to the correct processing.

    Parameters
    ----------
    session_content_hash: str
        The unique key (SHA256 hash of video content) for this session processing.
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
    caption_new_speaker_turn_pattern: Optional[str]
        Passthrough to sr_models.webvtt_sr_model.WebVTTSRModel.
    caption_confidence: Optional[float]
        Passthrough to sr_models.webvtt_sr_model.WebVTTSRModel.

    Returns
    -------
    transcript_uri: The URI to the uploaded transcript file.
    """
    # If no captions, generate transcript with Google Speech-to-Text
    if session.caption_uri is None:
        # TODO:
        # Get feeder phrases
        transcript = use_speech_to_text_and_generate_transcript(
            audio_uri=audio_uri,
            credentials_file=credentials_file,
        )

    # Process captions
    else:
        transcript = get_captions_and_generate_transcript(
            caption_uri=session.caption_uri,
            new_turn_pattern=caption_new_speaker_turn_pattern,
            confidence=caption_confidence,
        )

    # Add extra metadata and upload
    return finalize_and_archive_transcript(
        session_content_hash=session_content_hash,
        transcript=transcript,
        bucket=bucket,
        credentials_file=credentials_file,
        session=session,
    )  # type: ignore


@task(nout=2)
def get_video_and_generate_thumbnails(
    session_content_hash: str, video_uri: str, bucket: str, credentials_file: str
) -> Tuple[str, str]:
    return ("", "")


@task
def store_processed_session(
    session: Session,
    audio_uri: str,
    transcript_uri: str,
    static_thumbnail_uri: str,
    hover_thumbnail_uri: str,
) -> None:
    pass
