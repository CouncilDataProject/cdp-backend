#!/usr/bin/env python
# -*- coding: utf-8 -*-

from importlib import import_module
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Set, Tuple

from gcsfs import GCSFileSystem
from prefect import Flow, task
from prefect.tasks.control_flow import case, merge

from ..database import functions as db_functions
from ..file_store import functions as fs_functions
from ..sr_models import GoogleCloudSRModel, WebVTTSRModel
from ..utils import file_utils as file_util_functions
from ..version import __version__
from .ingestion_models import EventIngestionModel, Session
from .pipeline_config import EventGatherPipelineConfig
from .transcript_model import Transcript

###############################################################################


class SessionProcessingResult(NamedTuple):
    session: Session
    audio_uri: str
    transcript: Transcript
    transcript_uri: str
    static_thumbnail_uri: str
    hover_thumbnail_uri: str


def import_get_events_func(func_path: str) -> Callable:
    path, func_name = str(func_path).rsplit(".", 1)
    mod = import_module(path)

    return getattr(mod, func_name)


def create_event_gather_flow(config: EventGatherPipelineConfig) -> Flow:
    """
    Provided a function to gather new event information, create the Prefect Flow object
    to preview, run, or visualize.

    Parameters
    ----------
    config: EventGatherPipelineConfig
        Configuration options for the pipeline.

    Returns
    -------
    flow: Flow
        The constructed CDP Event Gather Pipeline as a Prefect Flow.
    """
    # Load get_events_func
    get_events_func = import_get_events_func(config.get_events_function_path)

    # Create flow
    with Flow("CDP Event Gather Pipeline") as flow:
        events: List[EventIngestionModel] = get_events_func()

        for event in events:
            session_processing_results: List[SessionProcessingResult] = []
            for session in event.sessions:
                # Get or create audio
                session_content_hash, audio_uri = get_video_and_split_audio(
                    video_uri=session.video_uri,
                    bucket=config.validated_gcs_bucket_name,
                    credentials_file=config.google_credentials_file,
                )

                # Generate transcript
                transcript_uri, transcript = generate_transcript(
                    session_content_hash=session_content_hash,
                    audio_uri=audio_uri,
                    session=session,
                    event=event,
                    bucket=config.validated_gcs_bucket_name,
                    credentials_file=config.google_credentials_file,
                    caption_new_speaker_turn_pattern=(
                        config.caption_new_speaker_turn_pattern
                    ),
                    caption_confidence=config.caption_confidence,
                )

                # Generate thumbnails
                (
                    static_thumbnail_uri,
                    hover_thumbnail_uri,
                ) = get_video_and_generate_thumbnails(
                    session_content_hash=session_content_hash,
                    video_uri=session.video_uri,
                    bucket=config.validated_gcs_bucket_name,
                    credentials_file=config.google_credentials_file,
                )

                # Store all processed and provided data
                session_processing_results.append(
                    compile_session_processing_result(  # type: ignore
                        session=session,
                        audio_uri=audio_uri,
                        transcript=transcript,
                        transcript_uri=transcript_uri,
                        static_thumbnail_uri=static_thumbnail_uri,
                        hover_thumbnail_uri=hover_thumbnail_uri,
                    )
                )

            # Process all metadata and store event
            store_event_processing_results(
                event=event,
                session_processing_results=session_processing_results,
                credentials_file=config.google_credentials_file,
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
    tmp_audio_filepath = f"{session_content_hash}-audio.wav"
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
def construct_speech_to_text_phrases_context(event: EventIngestionModel) -> List[str]:
    """
    Construct a list of phrases to use for Google Speech-to-Text speech adaption.

    See: https://cloud.google.com/speech-to-text/docs/speech-adaptation

    Parameters
    ----------
    event: EventIngestionModel
        The event details to pull context from.

    Returns
    -------
    phrases: List[str]
        Compiled list of strings to act as target weights for the model.

    Notes
    -----
    Phrases are added in order of importance until GCP phrase limits are met.
    The order of importance is defined as:
    1. body name
    2. event minutes item names
    3. councilmember names
    4. matter titles
    5. councilmember role titles
    """
    # Note: Google Speech-to-Text allows max 500 phrases
    phrases: Set[str] = set()

    PHRASE_LIMIT = 500
    CUM_CHAR_LIMIT = 9900

    # In line def for get character count
    # Google Speech-to-Text allows cumulative max 9900 characters
    def _get_total_char_count(phrases: Set[str]) -> int:
        chars = 0
        for phrase in phrases:
            chars += len(phrase)

        return chars

    def _get_if_added_sum(phrases: Set[str], next_addition: str) -> int:
        current_len = _get_total_char_count(phrases)
        return current_len + len(next_addition)

    def _within_limit(phrases: Set[str]) -> bool:
        return (
            _get_total_char_count(phrases) < CUM_CHAR_LIMIT
            and len(phrases) < PHRASE_LIMIT
        )

    # Get body name
    if _within_limit(phrases):
        if _get_if_added_sum(phrases, event.body.name) < CUM_CHAR_LIMIT:
            phrases.add(event.body.name)

    # Extras from event minutes items
    if event.event_minutes_items is not None:
        # Get minutes item name
        for event_minutes_item in event.event_minutes_items:
            if _within_limit(phrases):
                if (
                    _get_if_added_sum(phrases, event_minutes_item.minutes_item.name)
                    < CUM_CHAR_LIMIT
                ):
                    phrases.add(event_minutes_item.minutes_item.name)

        # Get councilmember names from sponsors and votes
        for event_minutes_item in event.event_minutes_items:
            if event_minutes_item.matter is not None:
                if event_minutes_item.matter.sponsors is not None:
                    for sponsor in event_minutes_item.matter.sponsors:
                        if _within_limit(phrases):
                            if (
                                _get_if_added_sum(phrases, sponsor.name)
                                < CUM_CHAR_LIMIT
                            ):
                                phrases.add(sponsor.name)
            if event_minutes_item.votes is not None:
                for vote in event_minutes_item.votes:
                    if _within_limit(phrases):
                        if (
                            _get_if_added_sum(phrases, vote.person.name)
                            < CUM_CHAR_LIMIT
                        ):
                            phrases.add(vote.person.name)

        # Get matter titles
        for event_minutes_item in event.event_minutes_items:
            if event_minutes_item.matter is not None:
                if _within_limit(phrases):
                    if (
                        _get_if_added_sum(phrases, event_minutes_item.matter.title)
                        < CUM_CHAR_LIMIT
                    ):
                        phrases.add(event_minutes_item.matter.title)

        # Get councilmember role titles from sponsors and votes
        for event_minutes_item in event.event_minutes_items:
            if event_minutes_item.matter is not None:
                if event_minutes_item.matter.sponsors is not None:
                    for sponsor in event_minutes_item.matter.sponsors:
                        if sponsor.roles is not None:
                            for role in sponsor.roles:
                                if (
                                    _get_if_added_sum(phrases, role.title)
                                    < CUM_CHAR_LIMIT
                                ):
                                    phrases.add(role.title)
            if event_minutes_item.votes is not None:
                for vote in event_minutes_item.votes:
                    if vote.person.roles is not None:
                        for role in vote.person.roles:
                            if _within_limit(phrases):
                                if (
                                    _get_if_added_sum(phrases, role.title)
                                    < CUM_CHAR_LIMIT
                                ):
                                    phrases.add(role.title)

    return list(phrases)


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


@task(nout=2)
def finalize_and_archive_transcript(
    transcript: Transcript,
    transcript_save_path: str,
    bucket: str,
    credentials_file: str,
    session: Session,
) -> Tuple[str, Transcript]:
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
    transcript_uri: str
        The URI of the stored transcript JSON.
    transcript: Transcript
        The finalized in memory Transcript object.
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

    return transcript_file_uri, transcript


@task(nout=4)
def check_for_existing_transcript(
    session_content_hash: str,
    bucket: str,
    credentials_file: str,
) -> Tuple[str, Optional[str], Optional[Transcript], bool]:
    """
    Check and load any existing transcript object.

    Parameters
    ----------
    session_content_hash: str
        The unique key (SHA256 hash of video content) for this session processing.
    bucket: str
        The bucket to store the transcript to.
    credentials_file: str
        Path to Google Service Account Credentials JSON file.

    Returns
    -------
    transcript_filename: str
        The filename of the transcript to create (or found).
    transcript_uri: Optional[str]
        If found, the transcript uri. Else, None.
    transcript: Optional[Transcript]
        If found, the loaded in-memory Transcript object. Else, None.
    transcript_exists: bool
        Boolean value for if the transcript was found or not.
        Required for downstream Prefect usage.
    """
    # Combine to transcript filename
    tmp_transcript_filepath = (
        f"{session_content_hash}-"
        f"cdp_{__version__.replace('.', '_')}-"
        f"transcript.json"
    )

    # Check for existing transcript
    transcript_uri = fs_functions.get_file_uri(
        bucket=bucket,
        filename=tmp_transcript_filepath,
        credentials_file=credentials_file,
    )
    transcript_exists = True if transcript_uri is not None else False

    # Load transcript if exists
    if transcript_exists:
        fs = GCSFileSystem(token=credentials_file)
        with fs.open(transcript_uri, "r") as open_resource:
            transcript = Transcript.from_json(open_resource.read())  # type: ignore
    else:
        transcript = None

    return (tmp_transcript_filepath, transcript_uri, transcript, transcript_exists)


def generate_transcript(
    session_content_hash: str,
    audio_uri: str,
    session: Session,
    event: EventIngestionModel,
    bucket: str,
    credentials_file: str,
    caption_new_speaker_turn_pattern: Optional[str] = None,
    caption_confidence: Optional[float] = None,
) -> Tuple[str, Transcript]:
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
    event: EventIngestionModel
        The parent event of the session. If no captions are available,
        speech context phrases will be pulled from the whole event details.
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
    transcript_uri: str
        The URI to the uploaded transcript file.
    transcript: Transcript
        The in-memory Transcript object.
    """
    # Get unique transcript name from parameters and current lib version
    (
        tmp_transcript_filepath,
        transcript_uri,
        transcript,
        transcript_exists,
    ) = check_for_existing_transcript(
        session_content_hash=session_content_hash,
        bucket=bucket,
        credentials_file=credentials_file,
    )

    # If no pre-existing transcript with the same parameters, generate
    with case(transcript_exists, False):
        # If no captions, generate transcript with Google Speech-to-Text
        if session.caption_uri is None:
            phrases = construct_speech_to_text_phrases_context(event=event)
            generated_transcript = use_speech_to_text_and_generate_transcript(
                audio_uri=audio_uri,
                credentials_file=credentials_file,
                phrases=phrases,
            )

        # Process captions
        else:
            generated_transcript = get_captions_and_generate_transcript(
                caption_uri=session.caption_uri,
                new_turn_pattern=caption_new_speaker_turn_pattern,
                confidence=caption_confidence,
            )

        # Add extra metadata and upload
        (
            generated_transcript_uri,
            generated_transcript,
        ) = finalize_and_archive_transcript(
            transcript=generated_transcript,
            transcript_save_path=tmp_transcript_filepath,
            bucket=bucket,
            credentials_file=credentials_file,
            session=session,
        )

    # Existing transcript
    with case(transcript_uri, True):
        found_transcript_uri = transcript_uri
        found_transcript = transcript

    return (
        merge(generated_transcript_uri, found_transcript_uri),  # type: ignore
        merge(generated_transcript, found_transcript),  # type: ignore
    )


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
    transcript: Transcript,
    transcript_uri: str,
    static_thumbnail_uri: str,
    hover_thumbnail_uri: str,
) -> SessionProcessingResult:
    return SessionProcessingResult(
        session=session,
        audio_uri=audio_uri,
        transcript=transcript,
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
    # Get high level event metadata and db models
    # Upload body
    body_db_model = db_functions.create_body_from_ingestion_model(body=event.body)
    body_db_model = db_functions.upload_db_model(
        db_model=body_db_model,
        credentials_file=credentials_file,
        ingestion_model=event.body,
    )

    # Upload event
    event_db_model = db_functions.create_event_from_ingestion_model(
        event=event,
        body_ref=body_db_model,
    )
    event_db_model = db_functions.upload_db_model(
        db_model=event_db_model,
        credentials_file=credentials_file,
        ingestion_model=event,
    )

    # Iter sessions
    for session_result in session_processing_results:
        # Upload audio file
        audio_file_db_model = db_functions.create_file(uri=session_result.audio_uri)
        audio_file_db_model = db_functions.upload_db_model(
            db_model=audio_file_db_model,
            credentials_file=credentials_file,
            exist_ok=True,
        )

        # Upload transcript file
        transcript_file_db_model = db_functions.create_file(
            uri=session_result.transcript_uri,
        )
        transcript_file_db_model = db_functions.upload_db_model(
            db_model=transcript_file_db_model,
            credentials_file=credentials_file,
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
            credentials_file=credentials_file,
            ingestion_model=session_result.session,
        )

        # Create transcript
        transcript_db_model = db_functions.create_transcript(
            transcript_file_ref=transcript_file_db_model,
            session_ref=session_db_model,
            transcript=session_result.transcript,
        )
        transcript_db_model = db_functions.upload_db_model(
            db_model=transcript_db_model,
            credentials_file=credentials_file,
        )
