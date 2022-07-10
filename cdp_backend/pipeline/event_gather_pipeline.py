#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta
from importlib import import_module
from operator import attrgetter
from pathlib import Path
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Set, Tuple, Union

from aiohttp.client_exceptions import ClientResponseError
from fireo.fields.errors import FieldValidationFailed, InvalidFieldType, RequiredField
from gcsfs import GCSFileSystem
from prefect import Flow, task
from prefect.tasks.control_flow import case, merge
from requests import ConnectionError

from ..database import constants as db_constants
from ..database import functions as db_functions
from ..database import models as db_models
from ..database.validators import is_secure_uri, resource_exists, try_url
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
    session_video_hosted_url: str
    session_content_hash: str
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
                # Download video to local copy
                resource_copy_filepath = resource_copy_task(uri=session.video_uri)

                # Get unique session identifier
                session_content_hash = get_session_content_hash(
                    tmp_video_filepath=resource_copy_filepath,
                )

                # Handle video conversion or non-secure resource
                # hosting
                (
                    tmp_video_filepath,
                    session_video_hosted_url,
                ) = convert_video_and_handle_host(
                    session_content_hash=session_content_hash,
                    video_filepath=resource_copy_filepath,
                    session=session,
                    credentials_file=config.google_credentials_file,
                    bucket=config.validated_gcs_bucket_name,
                )

                # Split audio and store
                audio_uri = split_audio(
                    session_content_hash=session_content_hash,
                    tmp_video_filepath=tmp_video_filepath,
                    bucket=config.validated_gcs_bucket_name,
                    credentials_file=config.google_credentials_file,
                )

                # Check caption uri
                if session.caption_uri is not None:
                    # If the caption doesn't exist, remove the property
                    # This will result in Speech-to-Text being used instead
                    if not resource_exists(session.caption_uri):
                        log.warning(
                            f"File not found using provided caption URI: "
                            f"'{session.caption_uri}'. "
                            f"Removing the referenced caption URI and will process "
                            f"the session using Speech-to-Text."
                        )
                        session.caption_uri = None

                # Generate transcript
                transcript_uri, transcript = generate_transcript(
                    session_content_hash=session_content_hash,  # type: ignore
                    audio_uri=audio_uri,  # type: ignore
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
                (static_thumbnail_uri, hover_thumbnail_uri,) = generate_thumbnails(
                    session_content_hash=session_content_hash,
                    tmp_video_path=tmp_video_filepath,
                    event=event,
                    bucket=config.validated_gcs_bucket_name,
                    credentials_file=config.google_credentials_file,
                )

                # Add audio uri and static thumbnail uri
                resource_delete_task(
                    tmp_video_filepath, upstream_tasks=[audio_uri, static_thumbnail_uri]
                )

                # Store all processed and provided data
                session_processing_results.append(
                    compile_session_processing_result(  # type: ignore
                        session=session,
                        session_video_hosted_url=session_video_hosted_url,
                        session_content_hash=session_content_hash,
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
            )

    return flow


@task(max_retries=3, retry_delay=timedelta(seconds=120))
def resource_copy_task(uri: str) -> str:
    """
    Copy a file to a temporary location for processing.

    Parameters
    ----------
    uri: str
        The URI to the file to copy.

    Returns
    -------
    local_path: str
        The local path to the copied file.

    Notes
    -----
    We sometimes get file downloading failures when running in parallel so this has two
    retries attached to it that will run after a failure on a 2 minute delay.
    """
    return file_utils.resource_copy(
        uri=uri,
        overwrite=True,
    )


@task
def resource_delete_task(uri: str) -> None:
    """
    Remove local file

    Parameters
    ----------
    uri: str
        The local video file.
    """
    fs_functions.remove_local_file(uri)


@task
def get_session_content_hash(
    tmp_video_filepath: str,
) -> str:
    """
    Hash the video file content to get a unique identifier for the session.

    Parameters
    ----------
    tmp_video_filepath: str
        The local path for video file to generate a hash for.

    Returns
    -------
    session_content_hash: str
        The unique key (SHA256 hash of video content) for this session processing.
    """
    # Hash the video contents
    return file_utils.hash_file_contents(uri=tmp_video_filepath)


@task(nout=2)
def convert_video_and_handle_host(
    session_content_hash: str,
    video_filepath: str,
    session: Session,
    credentials_file: str,
    bucket: str,
) -> Tuple[str, str]:
    """
    Convert a video to MP4 (if necessary), upload it to the file store, and remove
    the original non-MP4 file that was resource copied.

    Additionally, if the video is hosted from an unsecure resource, host it ourselves.

    Parameters
    ----------
    session_content_hash: str
        The content hash to use as the filename for the video once uploaded.
    video_filepath: Union[str, Path]
        The local path for video file to convert.
    session: Session
        The session to append the new MP4 video uri to.
    credentials_file: str
        Path to Google Service Account Credentials JSON file.
    bucket: str
        The GCS bucket to store the MP4 file to.

    Returns
    -------
    mp4_filepath: str
        The local filepath of the converted MP4 file.
    hosted_video_uri: str
        The URI for the CDP hosted video.
    """
    # Get file extension
    ext = Path(video_filepath).suffix.lower()

    # Convert to mp4 if file isn't of approved web format
    cdp_will_host = False
    if ext not in [".mp4", ".webm"]:
        cdp_will_host = True

        # Convert video to mp4
        mp4_filepath = file_utils.convert_video_to_mp4(video_filepath)

        # Remove old mkv file
        fs_functions.remove_local_file(video_filepath)

        # Update variable name for easier downstream typing
        video_filepath = mp4_filepath

    # Check if original session video uri is a m3u8
    # We cant follow the normal coonvert video process from above
    # because the m3u8 looks to the URI for all the chunks
    elif session.video_uri.endswith(".m3u8"):
        cdp_will_host = True

    # Store if the original host isn't https
    elif not is_secure_uri(session.video_uri):
        try:
            resource_uri = try_url(session.video_uri)
        except LookupError:
            # The provided URI could still be like GCS or S3 URI, which
            # works for download but not for streaming / hosting
            cdp_will_host = True
        else:
            if is_secure_uri(resource_uri):
                log.info(
                    f"Found secure version of {session.video_uri}, "
                    f"updating stored video URI."
                )
                hosted_video_media_url = resource_uri
            else:
                cdp_will_host = True
    else:
        hosted_video_media_url = session.video_uri

    # Upload and swap if cdp is hosting
    if cdp_will_host:
        # Upload to gcsfs
        log.info("Storing a copy of video to CDP filestore.")
        hosted_video_uri = fs_functions.upload_file(
            credentials_file=credentials_file,
            bucket=bucket,
            filepath=video_filepath,
            save_name=f"{session_content_hash}-video.mp4",
        )

        # Create fs to generate hosted media URL
        hosted_video_media_url = fs_functions.get_open_url_for_gcs_file(
            credentials_file=credentials_file,
            uri=hosted_video_uri,
        )

    return video_filepath, hosted_video_media_url


@task
def split_audio(
    session_content_hash: str,
    tmp_video_filepath: str,
    bucket: str,
    credentials_file: str,
) -> str:
    """
    Split the audio from a local video file.

    Parameters
    ----------
    session_content_hash: str
        The unique identifier for the session.
    tmp_video_filepath: str
        The local path for video file to generate a hash for.
    bucket: str
        The bucket to store the transcript to.
    credentials_file: str
        Path to Google Service Account Credentials JSON file.

    Returns
    -------
    audio_uri: str
        The URI to the uploaded audio file.
    """
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
            remove_local=True,
        )
        fs_functions.upload_file(
            credentials_file=credentials_file,
            bucket=bucket,
            filepath=tmp_audio_log_out_filepath,
            remove_local=True,
        )
        fs_functions.upload_file(
            credentials_file=credentials_file,
            bucket=bucket,
            filepath=tmp_audio_log_err_filepath,
            remove_local=True,
        )

    return audio_uri


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
        remove_local=True,
    )

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
def generate_thumbnails(
    session_content_hash: str,
    tmp_video_path: str,
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
    tmp_video_path: str
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
        remove_local=True,
    )

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
        remove_local=True,
    )

    return (
        static_thumbnail_url,
        hover_thumbnail_url,
    )


@task
def compile_session_processing_result(
    session: Session,
    session_video_hosted_url: str,
    session_content_hash: str,
    audio_uri: str,
    transcript: Transcript,
    transcript_uri: str,
    static_thumbnail_uri: str,
    hover_thumbnail_uri: str,
) -> SessionProcessingResult:
    return SessionProcessingResult(
        session=session,
        session_video_hosted_url=session_video_hosted_url,
        session_content_hash=session_content_hash,
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
    upload_cache: Dict[str, db_models.Person] = {},
) -> db_models.Person:
    # The JSON string of the whole person tree turns out to be a great cache key because
    # 1. we can hash strings (which means we can shove them into a dictionary)
    # 2. the JSON string store all of the attached seat and role information
    # So, if the same person is referenced multiple times in the ingestion model
    # but most of those references have the same data and only a few have different data
    # the produced JSON string will note the differences and run when it needs to.
    person_cache_key = person.to_json()  # type: ignore

    if person_cache_key not in upload_cache:
        # Store person picture file
        person_picture_db_model: Optional[db_models.File]
        if person.picture_uri is not None:
            try:
                tmp_person_picture_path = file_utils.resource_copy(
                    uri=person.picture_uri,
                    dst=f"{person.name}--person_picture",
                    overwrite=True,
                )
                destination_path = file_utils.generate_file_storage_name(
                    tmp_person_picture_path,
                    "person-picture",
                )
                person_picture_uri = fs_functions.upload_file(
                    credentials_file=credentials_file,
                    bucket=bucket,
                    filepath=tmp_person_picture_path,
                    save_name=destination_path,
                    remove_local=True,
                )
                person_picture_db_model = db_functions.create_file(
                    uri=person_picture_uri,
                    credentials_file=credentials_file,
                )
                person_picture_db_model = db_functions.upload_db_model(
                    db_model=person_picture_db_model,
                    credentials_file=credentials_file,
                )
            except (FileNotFoundError, ClientResponseError, ConnectionError) as e:
                person_picture_db_model = None
                log.error(
                    f"Person ('{person.name}'), picture URI could not be archived."
                    f"({person.picture_uri}). Error: {e}"
                )
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
        except (
            FieldValidationFailed,
            RequiredField,
            InvalidFieldType,
            ConnectionError,
        ):
            log.error(
                f"Person ({person_db_model.to_dict()}), "
                f"was missing required information. Generating minimum person details."
            )
            person_db_model = db_functions.create_minimal_person(person=person)
            # No ingestion model provided here so that we don't try to
            # re-validate the already failed model upload
            person_db_model = db_functions.upload_db_model(
                db_model=person_db_model,
                credentials_file=credentials_file,
            )

        # Update upload cache with person
        upload_cache[person_cache_key] = person_db_model

        # Create seat
        if person.seat is not None:
            # Store seat picture file
            person_seat_image_db_model: Optional[db_models.File]
            try:
                if person.seat.image_uri is not None:
                    tmp_person_seat_image_path = file_utils.resource_copy(
                        uri=person.seat.image_uri,
                        dst=f"{person.name}--{person.seat.name}--seat_image",
                        overwrite=True,
                    )
                    destination_path = file_utils.generate_file_storage_name(
                        tmp_person_seat_image_path,
                        "seat-image",
                    )
                    person_seat_image_uri = fs_functions.upload_file(
                        credentials_file=credentials_file,
                        bucket=bucket,
                        filepath=tmp_person_seat_image_path,
                        save_name=destination_path,
                        remove_local=True,
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

            except (FileNotFoundError, ClientResponseError, ConnectionError) as e:
                person_seat_image_db_model = None
                log.error(
                    f"Person ('{person.name}'), seat image URI could not be archived."
                    f"({person.seat.image_uri}). Error: {e}"
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
    else:
        person_db_model = upload_cache[person_cache_key]

    log.info(f"Completed metadata processing for '{person.name}'.")
    return person_db_model


def _calculate_in_majority(
    vote: ingestion_models.Vote,
    event_minutes_item: ingestion_models.EventMinutesItem,
) -> Optional[bool]:
    # Voted to Approve or Approve-by-abstention-or-absence
    if vote.decision in [
        db_constants.VoteDecision.APPROVE,
        db_constants.VoteDecision.ABSTAIN_APPROVE,
        db_constants.VoteDecision.ABSENT_APPROVE,
    ]:
        return (
            event_minutes_item.decision == db_constants.EventMinutesItemDecision.PASSED
        )

    # Voted to Reject or Reject-by-abstention-or-absence
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
    except (FieldValidationFailed, ConnectionError):
        log.error(
            f"Agenda and/or minutes docs could not be found. "
            f"Adding event without agenda and minutes URIs. "
            f"({event.agenda_uri} AND/OR {event.minutes_uri} do not exist)"
        )

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

        # Create session
        session_db_model = db_functions.create_session(
            session=session_result.session,
            session_video_hosted_url=session_result.session_video_hosted_url,
            session_content_hash=session_result.session_content_hash,
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
    processed_person_upload_cache: Dict[str, db_models.Person] = {}
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
                            upload_cache=processed_person_upload_cache,
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
                allowed_emi_decisions = constants_utils.get_all_class_attr_values(
                    db_constants.EventMinutesItemDecision
                )
                log.warning(
                    f"Provided 'decision' is not an approved constant. "
                    f"Provided: '{event_minutes_item.decision}' "
                    f"Should be one of: {allowed_emi_decisions} "
                    f"See: "
                    f"cdp_backend.database.constants.EventMinutesItemDecision. "
                    f"Creating EventMinutesItem without decision value."
                )

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
                    except (FieldValidationFailed, RequiredField):
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
                    try:
                        file_uri = try_url(supporting_file.uri)
                        supporting_file.uri = file_uri
                    except LookupError as e:
                        log.error(
                            f"SupportingFile ('{supporting_file.uri}') "
                            f"uri does not exist. Skipping. Error: {e}"
                        )
                        continue

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
                        except (
                            FieldValidationFailed,
                            ConnectionError,
                        ) as e:
                            log.error(
                                f"MatterFile ('{supporting_file.uri}') "
                                f"could not be archived. Skipping. Error: {e}"
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
                    except (FieldValidationFailed, ConnectionError) as e:
                        log.error(
                            f"EventMinutesItemFile ('{supporting_file.uri}') "
                            f"could not be archived. Error: {e}"
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
                            upload_cache=processed_person_upload_cache,
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
                        except (
                            FieldValidationFailed,
                            RequiredField,
                            InvalidFieldType,
                        ):
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
