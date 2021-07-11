#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Tuple

import fireo
from prefect import Flow, task

from ..database import functions as db_functions
from ..file_store import functions as fs_functions
from ..sr_models import GoogleCloudSRModel, WebVTTSRModel
from ..utils import file_utils as file_util_functions
from ..version import __version__
from .ingestion_models import EventIngestionModel, Session
from .transcript_model import Transcript

###############################################################################

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)4s: %(module)s:%(lineno)4s %(asctime)s] %(message)s",
)
log = logging.getLogger(__name__)

###############################################################################

# TODO:
# 2. move all db uploads to end
# 4. session database upload
# 5. tests

# DB TODOS:
# TODO: Either add ingestion model to upload_db_model_task call
# or support db model updates without ingestion model


class SessionProcessingResult(NamedTuple):
    session: Session
    audio_uri: str
    transcript_uri: str
    static_thumbnail_uri: str
    hover_thumbnail_uri: str


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
            session_processing_results: List[SessionProcessingResult] = []
            for session in event.sessions:
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
                session_processing_results.append(
                    compile_session_processing_result(  # type: ignore
                        session=session,
                        audio_uri=audio_uri,
                        transcript_uri=transcript_uri,
                        static_thumbnail_uri=static_thumbnail_uri,
                        hover_thumbnail_uri=hover_thumbnail_uri,
                    )
                )

            # Process all metadata and store event
            store_event_processing_results(
                event=event,
                session_processing_results=session_processing_results,
                credentials_file=credentials_file,
            )

    return flow


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
        fs_functions.upload_file(
            credentials_file=credentials_file,
            bucket=bucket,
            filepath=tmp_audio_log_out_filepath,
        )
        fs_functions.upload_file(
            credentials_file=credentials_file,
            bucket=bucket,
            filepath=tmp_audio_log_err_filepath,
        )

        # Remove tmp files after their final dependent tasks are finished
        for local_path in [
            tmp_audio_filepath,
            tmp_audio_log_out_filepath,
            tmp_audio_log_err_filepath,
        ]:
            fs_functions.remove_local_file(local_path)

    # Always remove tmp video file
    fs_functions.remove_local_file(tmp_video_filepath)

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
    transcript: Transcript,
    transcript_save_path: str,
    bucket: str,
    credentials_file: str,
    session: Session,
) -> str:
    """
    Finalizes metadata for a Transcript object, stores the transcript as JSON to object
    storage and finally adds transcript and file objects to database.

    Parameters
    ----------
    transcript: Transcript
        The transcript to finish processing and store.
    transcript_save_path: str
        The path (or filename) to save the transcript at in the bucket.
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
    with open(transcript_save_path, "w") as open_resource:
        open_resource.write(transcript.to_json())  # type: ignore

    # Store to file store
    transcript_file_uri = fs_functions.upload_file(
        credentials_file=credentials_file,
        bucket=bucket,
        filepath=transcript_save_path,
    )

    # Remove local transcript
    fs_functions.remove_local_file(transcript_save_path)

    return transcript_file_uri


@task
def hash_transcription_parameters_for_filename(
    session_content_hash: str,
    session: Session,
) -> str:
    # Get transcription params uniqueness
    # Dump session to JSON and hash
    tmp_session_storage = f"{session_content_hash}-session.json"
    with open(tmp_session_storage, "w") as open_resource:
        open_resource.write(session.to_json())  # type: ignore

    # Get hash of full session parameters
    session_parameters_hash = file_util_functions.hash_file_contents(
        uri=tmp_session_storage,
    )

    # Remove local session file
    fs_functions.remove_local_file(tmp_session_storage)

    # Combine to transcript filename
    return (
        f"{session_content_hash}-"
        f"{session_parameters_hash}-"
        f"cdp_{__version__.replace('.', '_')}-"
        f"transcript.json"
    )


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
    # Get unique transcript name from parameters and current lib version
    tmp_transcript_filepath = hash_transcription_parameters_for_filename(
        session_content_hash=session_content_hash,
        session=session,
    )

    # Check for existing transcript
    transcript_uri = fs_functions.get_file_uri(
        bucket=bucket,
        filename=tmp_transcript_filepath,  # type: ignore
        credentials_file=credentials_file,
    )

    # If no pre-existing transcript with the same parameters, generate
    if transcript_uri is None:
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
        return finalize_and_archive_transcript(  # type: ignore
            transcript=transcript,
            transcript_save_path=tmp_transcript_filepath,
            bucket=bucket,
            credentials_file=credentials_file,
            session=session,
        )
    else:
        return transcript_uri


@task(nout=2)
def get_video_and_generate_thumbnails(
    session_content_hash: str, video_uri: str, bucket: str, credentials_file: str
) -> Tuple[str, str]:
    return (
        f"{session_content_hash}-static-thumb.png",
        f"{session_content_hash}-hover-thumb.gif",
    )


@task
def compile_session_processing_result(
    session: Session,
    audio_uri: str,
    transcript_uri: str,
    static_thumbnail_uri: str,
    hover_thumbnail_uri: str,
) -> SessionProcessingResult:
    return SessionProcessingResult(
        session=session,
        audio_uri=audio_uri,
        transcript_uri=transcript_uri,
        static_thumbnail_uri=static_thumbnail_uri,
        hover_thumbnail_uri=hover_thumbnail_uri,
    )


@task
def store_event_processing_results(
    event: EventIngestionModel,
    session_processing_results: List[SessionProcessingResult],
    credentials_file: str,
) -> None:
    # Init transaction and auth
    fireo.connection(from_file=credentials_file)

    # Get high level event metadata and db models
    # Upload body
    body_db_model = db_functions.create_body_from_ingestion_model(body=event.body)
    body_db_model = db_functions.upload_db_model(
        db_model=body_db_model,
        ingestion_model=event.body,
    )

    # Upload event
    event_db_model = db_functions.create_event_from_ingestion_model(
        event=event,
        body_ref=body_db_model,
    )
    event_db_model = db_functions.upload_db_model(
        db_model=event_db_model,
        ingestion_model=event,
    )

    # Iter sessions
    for session_result in session_processing_results:
        # Upload audio file
        audio_file_db_model = db_functions.create_file(uri=session_result.audio_uri)
        audio_file_db_model = db_functions.upload_db_model(
            db_model=audio_file_db_model,
            exist_ok=True,
        )

        # Upload transcript file
        transcript_file_db_model = db_functions.create_file(
            uri=session_result.transcript_uri,
        )
        transcript_file_db_model = db_functions.upload_db_model(
            db_model=transcript_file_db_model,
            exist_ok=True,
        )

        # Upload static thumbnail
        # static_thumbnail_file_db_model = db_functions.create_file(
        #     uri=session_result.static_thumbnail_uri,
        # )
        # static_thumbnail_file_db_model = db_functions.upload_db_model(
        #     db_model=static_thumbnail_file_db_model,
        #     exist_ok=True,
        # )

        # Upload hover thumbnail
        # hover_thumbnail_file_db_model = db_functions.create_file(
        #     uri=session_result.hover_thumbnail_uri,
        # )
        # hover_thumbnail_file_db_model = db_functions.upload_db_model(
        #     db_model=hover_thumbnail_file_db_model,
        #     exist_ok=True,
        # )

        # Create session
        session_db_model = db_functions.create_session_from_ingestion_model(
            session=session_result.session,
            event_ref=event_db_model,
        )
        session_db_model = db_functions.upload_db_model(
            db_model=session_db_model,
            ingestion_model=session_result.session,
        )

        # Create transcript
        # transcript_db_model = db_functions.create_transcript(
        #     transcript_file_ref=transcript_file_db_model,
        #     session_ref=session_db_model,
        #     transcript=transcript,
        # )
