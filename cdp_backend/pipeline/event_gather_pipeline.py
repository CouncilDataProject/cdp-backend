#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import tempfile
from datetime import datetime, timedelta
from importlib import import_module
from operator import attrgetter
from pathlib import Path
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Set, Tuple, Union

from fireo.fields.errors import FieldValidationFailed, InvalidFieldType, RequiredField
from fsspec.core import url_to_fs
from gcsfs import GCSFileSystem
from prefect import Flow, task
from prefect.tasks.control_flow import case, merge

from ..database import constants as db_constants
from ..database import functions as db_functions
from ..database import models as db_models
from ..file_store import functions as fs_functions
from ..sr_models import GoogleCloudSRModel, WebVTTSRModel
from ..utils import constants_utils, file_utils
from ..version import __version__
from . import ingestion_models
from .ingestion_models import EventIngestionModel, Session
from .pipeline_config import EventGatherPipelineConfig
from .transcript_model import Transcript

###############################################################################

log = logging.getLogger(__name__)

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


def create_event_gather_flow(
    config: EventGatherPipelineConfig,
    from_dt: Optional[Union[str, datetime]] = None,
    to_dt: Optional[Union[str, datetime]] = None,
    prefetched_events: Optional[List[EventIngestionModel]] = None,
    from_local: bool = False,
) -> Flow:
    """
    Provided a function to gather new event information, create the Prefect Flow object
    to preview, run, or visualize.

    Parameters
    ----------
    config: EventGatherPipelineConfig
        Configuration options for the pipeline.
    from_dt: Optional[Union[str, datetime]]
        Optional ISO formatted string or datetime object to pass to the get_events
        function to act as the start point for event gathering.
        Default: None (two days ago)
    to_dt: Optional[Union[str, datetime]]
        Optional ISO formatted string or datetime object to pass to the get_events
        function to act as the end point for event gathering.
        Default: None (now)

    Returns
    -------
    flow: Flow
        The constructed CDP Event Gather Pipeline as a Prefect Flow.
    """
    # Load get_events_func
    get_events_func = import_get_events_func(config.get_events_function_path)

    # Handle from datetime
    if isinstance(from_dt, str) and len(from_dt) != 0:
        from_datetime = datetime.fromisoformat(from_dt)
    elif isinstance(from_dt, datetime):
        from_datetime = from_dt
    else:
        from_datetime = datetime.utcnow() - timedelta(
            days=config.default_event_gather_from_days_timedelta,
        )

    # Handle to datetime
    if isinstance(to_dt, str) and len(to_dt) != 0:
        to_datetime = datetime.fromisoformat(to_dt)
    elif isinstance(to_dt, datetime):
        to_datetime = to_dt
    else:
        to_datetime = datetime.utcnow()

    # Create flow
    with Flow("CDP Event Gather Pipeline") as flow:
        log.info(
            f"Gathering events to process. "
            f"({from_datetime.isoformat()} - {to_datetime.isoformat()})"
        )

        # Use prefetched events instead of get_events_func if provided
        if prefetched_events is not None:
            events = prefetched_events

        else:
            events = get_events_func(
                from_dt=from_datetime,
                to_dt=to_datetime,
            )

        # Safety measure catch
        if events is None:
            events = []
        log.info(f"Processing {len(events)} events.")

        for event in events:
            session_processing_results: List[SessionProcessingResult] = []
            for session in event.sessions:
                # Get or create audio
                session_content_hash, audio_uri = get_video_and_split_audio(
                    video_uri=session.video_uri,
                    bucket=config.validated_gcs_bucket_name,
                    credentials_file=config.google_credentials_file,
                )

                # Check caption uri
                if session.caption_uri is not None:
                    fs, caption_path = url_to_fs(session.caption_uri)

                    # If the caption doesn't exist, remove the property
                    # This will result in Speech-to-Text being used instead
                    if not fs.exists(caption_path):
                        log.warning(
                            f"File not found using provided caption URI: "
                            f"'{session.caption_uri}'. "
                            f"Removing the referenced caption URI and will process "
                            f"the session using Speech-to-Text."
                        )
                        session.caption_uri = None

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
                    event=event,
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
                bucket=config.validated_gcs_bucket_name,
                from_local=from_local,
            )

    return flow


@task(nout=2, max_retries=3, retry_delay=timedelta(seconds=60))
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

    Notes
    -----
    We sometimes get file downloading failures when running in parallel so this has two
    retries attached to it that will run after a failure on a 3 minute delay.
    """
    # Get just the video filename from the full uri
    # TODO: Handle windows file splitting???
    # Generally this is a URI but we do have a goal of a local file processing too...
    video_filename = video_uri.split("/")[-1]
    tmp_video_filepath = file_utils.resource_copy(
        uri=video_uri,
        dst=f"audio-splitting-{video_filename}",
        overwrite=True,
    )

    # Hash the video contents
    session_content_hash = file_utils.hash_file_contents(uri=tmp_video_filepath)

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
        ) = file_utils.split_audio(
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
                        if sponsor.seat is not None:
                            if sponsor.seat.roles is not None:
                                for role in sponsor.seat.roles:
                                    if (
                                        _get_if_added_sum(phrases, role.title)
                                        < CUM_CHAR_LIMIT
                                    ):
                                        phrases.add(role.title)
            if event_minutes_item.votes is not None:
                for vote in event_minutes_item.votes:
                    if vote.person.seat is not None:
                        if vote.person.seat.roles is not None:
                            for role in vote.person.seat.roles:
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
    local_captions = file_utils.resource_copy(
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
        The specific session details to be used in final transcript upload and
        archival.
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
    with case(transcript_exists, True):
        found_transcript_uri = transcript_uri
        found_transcript = transcript

    # Merge the two paths and results
    # Set the names of the merge for visualization and testing purposes
    result_transcript_uri = merge(
        generated_transcript_uri,
        found_transcript_uri,
    )
    result_transcript_uri.name = "merge_transcript_uri"
    result_transcript = merge(
        generated_transcript,
        found_transcript,
    )
    result_transcript.name = "merge_in_memory_transcript"

    return (result_transcript_uri, result_transcript)  # type: ignore


@task(nout=2)
def get_video_and_generate_thumbnails(
    session_content_hash: str,
    video_uri: str,
    event: EventIngestionModel,
    bucket: str,
    credentials_file: str,
) -> Tuple[str, str]:
    """
    Creates static and hover thumbnails.

    Parameters
    ----------
    session_content_hash: str
        The unique key (SHA256 hash of video content) for this session processing.
    video_uri: str
        The URI to the video file to generate thumbnails from.
    event: EventIngestionModel
        The parent event of the session. If no captions are available,
        speech context phrases will be pulled from the whole event details.
    bucket: str
        The name of the GCS bucket to upload the produced audio to.
    credentials_file: str
        Path to Google Service Account Credentials JSON file.

    Returns
    -------
    static_thumbnail_url: str
        The URL of the static thumbnail, stored on GCS.
    hover_thumbnail_url: str
        The URL of the hover thumbnail, stored on GCS.
    """
    # Create tmp directory to save file in
    dirpath = tempfile.mkdtemp()
    dst = Path(dirpath)

    tmp_video_path = file_utils.resource_copy(uri=video_uri, dst=dst)

    if event.static_thumbnail_uri is None:
        # Generate new
        static_thumbnail_file = file_utils.get_static_thumbnail(
            tmp_video_path, session_content_hash
        )
    else:
        static_thumbnail_file = file_utils.resource_copy(
            event.static_thumbnail_uri, session_content_hash
        )

    static_thumbnail_url = fs_functions.upload_file(
        credentials_file=credentials_file,
        bucket=bucket,
        filepath=static_thumbnail_file,
    )
    fs_functions.remove_local_file(static_thumbnail_file)

    if event.hover_thumbnail_uri is None:
        # Generate new
        hover_thumbnail_file = file_utils.get_hover_thumbnail(
            tmp_video_path, session_content_hash
        )
    else:
        hover_thumbnail_file = file_utils.resource_copy(
            event.hover_thumbnail_uri, session_content_hash
        )

    hover_thumbnail_url = fs_functions.upload_file(
        credentials_file=credentials_file,
        bucket=bucket,
        filepath=hover_thumbnail_file,
    )
    fs_functions.remove_local_file(hover_thumbnail_file)

    fs_functions.remove_local_file(tmp_video_path)

    return (
        static_thumbnail_url,
        hover_thumbnail_url,
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


def _process_person_ingestion(
    person: ingestion_models.Person,
    default_session: Session,
    credentials_file: str,
    bucket: str,
) -> db_models.Person:
    # Store person picture file
    person_picture_db_model: Optional[db_models.File]
    if person.picture_uri is not None:
        try:
            tmp_person_picture_path = file_utils.resource_copy(person.picture_uri)
            person_picture_uri = fs_functions.upload_file(
                credentials_file=credentials_file,
                bucket=bucket,
                filepath=tmp_person_picture_path,
            )
            fs_functions.remove_local_file(tmp_person_picture_path)
            person_picture_db_model = db_functions.create_file(
                uri=person_picture_uri,
                credentials_file=credentials_file,
            )
            person_picture_db_model = db_functions.upload_db_model(
                db_model=person_picture_db_model,
                credentials_file=credentials_file,
            )
        except FileNotFoundError:
            person_picture_db_model = None
            log.error(f"Person ('{person.name}'), picture URI could not be archived.")
    else:
        person_picture_db_model = None

    # Create person
    try:
        person_db_model = db_functions.create_person(
            person=person,
            picture_ref=person_picture_db_model,
            credentials_file=credentials_file,
        )
        person_db_model = db_functions.upload_db_model(
            db_model=person_db_model,
            credentials_file=credentials_file,
        )
    except (FieldValidationFailed, RequiredField, InvalidFieldType):
        person_db_model = db_functions.create_minimal_person(person=person)
        # No ingestion model provided here so that we don't try to
        # re-validate the already failed model upload
        person_db_model = db_functions.upload_db_model(
            db_model=person_db_model,
            credentials_file=credentials_file,
        )

    # Create seat
    if person.seat is not None:
        # Store seat picture file
        person_seat_image_db_model: Optional[db_models.File]
        try:
            if person.seat.image_uri is not None:
                tmp_person_seat_image_path = file_utils.resource_copy(
                    uri=person.seat.image_uri,
                )
                person_seat_image_uri = fs_functions.upload_file(
                    credentials_file=credentials_file,
                    bucket=bucket,
                    filepath=tmp_person_seat_image_path,
                )
                fs_functions.remove_local_file(
                    tmp_person_seat_image_path,
                )
                person_seat_image_db_model = db_functions.create_file(
                    uri=person_seat_image_uri, credentials_file=credentials_file
                )
                person_seat_image_db_model = db_functions.upload_db_model(
                    db_model=person_seat_image_db_model,
                    credentials_file=credentials_file,
                )
            else:
                person_seat_image_db_model = None
        except FileNotFoundError:
            person_seat_image_db_model = None
            log.error(
                f"Person ('{person.name}'), " f"seat image URI could not be archived."
            )

        # Actual seat creation
        person_seat_db_model = db_functions.create_seat(
            seat=person.seat,
            image_ref=person_seat_image_db_model,
        )
        person_seat_db_model = db_functions.upload_db_model(
            db_model=person_seat_db_model,
            credentials_file=credentials_file,
        )

        # Create roles
        if person.seat.roles is not None:
            for person_role in person.seat.roles:
                # Create any bodies for roles
                person_role_body_db_model: Optional[db_models.Body]
                if person_role.body is not None:
                    # Use or default role body start_datetime
                    if person_role.body.start_datetime is None:
                        person_role_body_start_datetime = (
                            default_session.session_datetime
                        )
                    else:
                        person_role_body_start_datetime = (
                            person_role.body.start_datetime
                        )

                    person_role_body_db_model = db_functions.create_body(
                        body=person_role.body,
                        start_datetime=person_role_body_start_datetime,
                    )
                    person_role_body_db_model = db_functions.upload_db_model(
                        db_model=person_role_body_db_model,
                        credentials_file=credentials_file,
                    )
                else:
                    person_role_body_db_model = None

                # Use or default role start_datetime
                if person_role.start_datetime is None:
                    person_role_start_datetime = default_session.session_datetime
                else:
                    person_role_start_datetime = person_role.start_datetime

                # Actual role creation
                person_role_db_model = db_functions.create_role(
                    role=person_role,
                    person_ref=person_db_model,
                    seat_ref=person_seat_db_model,
                    start_datetime=person_role_start_datetime,
                    body_ref=person_role_body_db_model,
                )
                person_role_db_model = db_functions.upload_db_model(
                    db_model=person_role_db_model,
                    credentials_file=credentials_file,
                )

    return person_db_model


def _calculate_in_majority(
    vote: ingestion_models.Vote,
    event_minutes_item: ingestion_models.EventMinutesItem,
) -> Optional[bool]:
    # Voted to Approve or Approve-by-abstention-or-absense
    if vote.decision in [
        db_constants.VoteDecision.APPROVE,
        db_constants.VoteDecision.ABSTAIN_APPROVE,
        db_constants.VoteDecision.ABSENT_APPROVE,
    ]:
        return (
            event_minutes_item.decision == db_constants.EventMinutesItemDecision.PASSED
        )

    # Voted to Reject or Reject-by-abstention-or-absense
    elif vote.decision in [
        db_constants.VoteDecision.REJECT,
        db_constants.VoteDecision.ABSTAIN_REJECT,
        db_constants.VoteDecision.ABSENT_REJECT,
    ]:
        return (
            event_minutes_item.decision == db_constants.EventMinutesItemDecision.FAILED
        )

    # Explicit return None for "was turn absent or abstain"
    return None


@task
def store_event_processing_results(
    event: EventIngestionModel,
    session_processing_results: List[SessionProcessingResult],
    credentials_file: str,
    bucket: str,
    from_local: bool = False,
) -> None:
    # TODO: check metadata before pipeline runs to avoid the many try excepts

    # Get first session
    first_session = min(event.sessions, key=attrgetter("session_index"))

    # Get high level event metadata and db models

    # Use or default body start_datetime
    if event.body.start_datetime is None:
        body_start_datetime = first_session.session_datetime
    else:
        body_start_datetime = event.body.start_datetime

    # Upload body
    body_db_model = db_functions.create_body(
        body=event.body,
        start_datetime=body_start_datetime,
    )
    body_db_model = db_functions.upload_db_model(
        db_model=body_db_model,
        credentials_file=credentials_file,
    )

    event_static_thumbnail_file_db_model = None
    event_hover_thumbnail_file_db_model = None

    for session_result in session_processing_results:
        # Upload static thumbnail
        static_thumbnail_file_db_model = db_functions.create_file(
            uri=session_result.static_thumbnail_uri,
            credentials_file=credentials_file,
        )
        static_thumbnail_file_db_model = db_functions.upload_db_model(
            db_model=static_thumbnail_file_db_model,
            credentials_file=credentials_file,
        )
        if event_static_thumbnail_file_db_model is None:
            event_static_thumbnail_file_db_model = static_thumbnail_file_db_model

        # Upload hover thumbnail
        hover_thumbnail_file_db_model = db_functions.create_file(
            uri=session_result.hover_thumbnail_uri,
            credentials_file=credentials_file,
        )
        hover_thumbnail_file_db_model = db_functions.upload_db_model(
            db_model=hover_thumbnail_file_db_model,
            credentials_file=credentials_file,
        )
        if event_hover_thumbnail_file_db_model is None:
            event_hover_thumbnail_file_db_model = hover_thumbnail_file_db_model

    # Upload event
    try:
        event_db_model = db_functions.create_event(
            body_ref=body_db_model,
            event_datetime=first_session.session_datetime,
            static_thumbnail_ref=event_static_thumbnail_file_db_model,
            hover_thumbnail_ref=event_hover_thumbnail_file_db_model,
            agenda_uri=event.agenda_uri,
            minutes_uri=event.minutes_uri,
            external_source_id=event.external_source_id,
            credentials_file=credentials_file,
        )
        event_db_model = db_functions.upload_db_model(
            db_model=event_db_model,
            credentials_file=credentials_file,
        )
    except FieldValidationFailed:
        event_db_model = db_functions.create_event(
            body_ref=body_db_model,
            event_datetime=first_session.session_datetime,
            static_thumbnail_ref=event_static_thumbnail_file_db_model,
            hover_thumbnail_ref=event_hover_thumbnail_file_db_model,
            external_source_id=event.external_source_id,
            credentials_file=credentials_file,
        )
        event_db_model = db_functions.upload_db_model(
            db_model=event_db_model,
            credentials_file=credentials_file,
        )

    # Iter sessions
    for session_result in session_processing_results:
        # Upload audio file
        audio_file_db_model = db_functions.create_file(
            uri=session_result.audio_uri,
            credentials_file=credentials_file,
        )
        audio_file_db_model = db_functions.upload_db_model(
            db_model=audio_file_db_model,
            credentials_file=credentials_file,
        )

        # Upload transcript file
        transcript_file_db_model = db_functions.create_file(
            uri=session_result.transcript_uri,
            credentials_file=credentials_file,
        )
        transcript_file_db_model = db_functions.upload_db_model(
            db_model=transcript_file_db_model,
            credentials_file=credentials_file,
        )

        # Account for uri's from local files
        if from_local:
            fs = GCSFileSystem(token=credentials_file)
            stream_url = str(fs.url(session_result.session.video_uri))
            session_result.session.video_uri = stream_url

        # Create session
        session_db_model = db_functions.create_session(
            session=session_result.session,
            event_ref=event_db_model,
            credentials_file=credentials_file,
        )
        session_db_model = db_functions.upload_db_model(
            db_model=session_db_model,
            credentials_file=credentials_file,
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

    # Add event metadata
    if event.event_minutes_items is not None:
        for emi_index, event_minutes_item in enumerate(event.event_minutes_items):
            if event_minutes_item.matter is not None:
                # Create matter
                matter_db_model = db_functions.create_matter(
                    matter=event_minutes_item.matter,
                )
                matter_db_model = db_functions.upload_db_model(
                    db_model=matter_db_model,
                    credentials_file=credentials_file,
                )

                # Add people from matter sponsors
                if event_minutes_item.matter.sponsors is not None:
                    for sponsor_person in event_minutes_item.matter.sponsors:
                        sponsor_person_db_model = _process_person_ingestion(
                            person=sponsor_person,
                            default_session=first_session,
                            credentials_file=credentials_file,
                            bucket=bucket,
                        )

                        # Create matter sponsor association
                        matter_sponsor_db_model = db_functions.create_matter_sponsor(
                            matter_ref=matter_db_model,
                            person_ref=sponsor_person_db_model,
                        )
                        matter_sponsor_db_model = db_functions.upload_db_model(
                            db_model=matter_sponsor_db_model,
                            credentials_file=credentials_file,
                        )

            else:
                matter_db_model = None  # type: ignore

            # Create minutes item
            minutes_item_db_model = db_functions.create_minutes_item(
                minutes_item=event_minutes_item.minutes_item,
                matter_ref=matter_db_model,
            )
            minutes_item_db_model = db_functions.upload_db_model(
                db_model=minutes_item_db_model,
                credentials_file=credentials_file,
            )

            # Handle event minutes item index
            if event_minutes_item.index is None:
                event_minutes_item_index = emi_index
            else:
                event_minutes_item_index = event_minutes_item.index

            # Create event minutes item
            try:
                event_minutes_item_db_model = db_functions.create_event_minutes_item(
                    event_minutes_item=event_minutes_item,
                    event_ref=event_db_model,
                    minutes_item_ref=minutes_item_db_model,
                    index=event_minutes_item_index,
                )
                event_minutes_item_db_model = db_functions.upload_db_model(
                    db_model=event_minutes_item_db_model,
                    credentials_file=credentials_file,
                )
            except (FieldValidationFailed, InvalidFieldType):
                event_minutes_item_db_model = (
                    db_functions.create_minimal_event_minutes_item(
                        event_ref=event_db_model,
                        minutes_item_ref=minutes_item_db_model,
                        index=event_minutes_item_index,
                    )
                )
                event_minutes_item_db_model = db_functions.upload_db_model(
                    db_model=event_minutes_item_db_model,
                    credentials_file=credentials_file,
                )

            # Create matter status
            if matter_db_model is not None and event_minutes_item.matter is not None:
                if event_minutes_item.matter.result_status is not None:
                    matter_status_db_model = db_functions.create_matter_status(
                        matter_ref=matter_db_model,
                        event_minutes_item_ref=event_minutes_item_db_model,
                        status=event_minutes_item.matter.result_status,
                        update_datetime=first_session.session_datetime,
                    )
                    try:
                        matter_status_db_model = db_functions.upload_db_model(
                            db_model=matter_status_db_model,
                            credentials_file=credentials_file,
                        )
                    except FieldValidationFailed:
                        allowed_matter_decisions = (
                            constants_utils.get_all_class_attr_values(
                                db_constants.MatterStatusDecision
                            )
                        )
                        log.error(
                            f"Provided 'status' is not an approved constant. "
                            f"Provided: '{event_minutes_item.matter.result_status}' "
                            f"Should be one of: {allowed_matter_decisions} "
                            f"See: "
                            f"cdp_backend.database.constants.MatterStatusDecision. "
                            f"Skipping matter status database upload."
                        )

            # Add supporting files for matter and event minutes item
            if event_minutes_item.supporting_files is not None:
                for supporting_file in event_minutes_item.supporting_files:

                    # Archive as matter file
                    if event_minutes_item.matter is not None:
                        try:
                            matter_file_db_model = db_functions.create_matter_file(
                                matter_ref=matter_db_model,
                                supporting_file=supporting_file,
                                credentials_file=credentials_file,
                            )
                            matter_file_db_model = db_functions.upload_db_model(
                                db_model=matter_file_db_model,
                                credentials_file=credentials_file,
                            )
                        except FieldValidationFailed:
                            log.error(
                                f"MatterFile ('{supporting_file.uri}') "
                                f"could not be archived."
                            )

                    # Archive as event minutes item file
                    try:
                        event_minutes_item_file_db_model = (
                            db_functions.create_event_minutes_item_file(
                                event_minutes_item_ref=event_minutes_item_db_model,
                                supporting_file=supporting_file,
                                credentials_file=credentials_file,
                            )
                        )
                        event_minutes_item_file_db_model = db_functions.upload_db_model(
                            db_model=event_minutes_item_file_db_model,
                            credentials_file=credentials_file,
                        )
                    except FieldValidationFailed:
                        log.error(
                            f"EventMinutesItemFile ('{supporting_file.uri}') "
                            f"could not be archived."
                        )

            # Add vote information
            if event_minutes_item.votes is not None:
                # Protect against corrupted data
                if (
                    event_minutes_item.decision is not None
                    and event_minutes_item.matter is not None
                ):
                    for vote in event_minutes_item.votes:
                        # Add people from voters
                        vote_person_db_model = _process_person_ingestion(
                            person=vote.person,
                            default_session=first_session,
                            credentials_file=credentials_file,
                            bucket=bucket,
                        )

                        # Create vote
                        try:
                            vote_db_model = db_functions.create_vote(
                                matter_ref=matter_db_model,
                                event_ref=event_db_model,
                                event_minutes_item_ref=event_minutes_item_db_model,
                                person_ref=vote_person_db_model,
                                decision=vote.decision,
                                in_majority=_calculate_in_majority(
                                    vote=vote,
                                    event_minutes_item=event_minutes_item,
                                ),
                                external_source_id=vote.external_source_id,
                            )
                            vote_db_model = db_functions.upload_db_model(
                                db_model=vote_db_model,
                                credentials_file=credentials_file,
                            )
                        except (FieldValidationFailed, RequiredField, InvalidFieldType):
                            allowed_vote_decisions = (
                                constants_utils.get_all_class_attr_values(
                                    db_constants.VoteDecision
                                )
                            )
                            log.error(
                                f"Provided 'decision' is not an approved constant. "
                                f"Provided: '{vote.decision}' "
                                f"Should be one of: {allowed_vote_decisions} "
                                f"See: cdp_backend.database.constants.VoteDecision. "
                                f"Skipping vote database upload."
                            )

                else:
                    log.error(
                        f"Unable to process voting information for event minutes item: "
                        f"'{event_minutes_item.minutes_item.name}'. "
                        f"Votes were present but overall decision for the "
                        f"event minutes item was 'None'."
                    )
