#!/usr/bin/env python

from __future__ import annotations

import http.client
import logging
from datetime import datetime, timedelta
from importlib import import_module
from operator import attrgetter
from pathlib import Path
from typing import Callable, NamedTuple
from uuid import uuid4

import backoff
from aiohttp.client_exceptions import ClientResponseError
from fireo.fields.errors import FieldValidationFailed, InvalidFieldType, RequiredField
from gcsfs import GCSFileSystem
from prefect import Flow, task
from prefect.tasks.control_flow import case, merge
from requests import ConnectionError

from .. import __version__
from ..database import constants as db_constants
from ..database import functions as db_functions
from ..database import models as db_models
from ..database.validators import is_secure_uri, resource_exists, try_url
from ..file_store import functions as fs_functions
from ..sr_models import WhisperModel
from ..utils import constants_utils, file_utils
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


@backoff.on_exception(
    backoff.expo,
    http.client.HTTPException,
    max_tries=3,
)
def get_events_with_backoff(
    func: Callable,
    start_dt: datetime,
    end_dt: datetime,
) -> list[ingestion_models.EventIngestionModel]:
    return func(from_dt=start_dt, to_dt=end_dt)


def create_event_gather_flow(
    config: EventGatherPipelineConfig,
    from_dt: str | datetime | None = None,
    to_dt: str | datetime | None = None,
    prefetched_events: list[EventIngestionModel] | None = None,
) -> Flow:
    """
    Create the Prefect Flow object to preview, run, or visualize.

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
    prefetched_events: Optional[List[EventIngestionModel]]
        A list of events to process instead of running the scraper found in the config.
        Default: None (use the scraper from the config)

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
            # Run the get events
            events = get_events_with_backoff(
                get_events_func,
                start_dt=from_datetime,
                end_dt=to_datetime,
            )

        # Safety measure catch
        if events is None:
            events = []

        log.info(f"Processing {len(events)} events.")
        for event in events:
            session_processing_results: list[SessionProcessingResult] = []
            for session in event.sessions:
                # Download video to local copy making
                # copy unique in case of shared session video
                resource_copy_filepath = resource_copy_task(
                    uri=session.video_uri,
                    dst=f"{str(uuid4())}_temp",
                    copy_suffix=True,
                )

                # Handle video conversion or non-secure resource
                # hosting
                (
                    tmp_video_filepath,
                    session_video_hosted_url,
                    session_content_hash,
                ) = convert_video_and_handle_host(
                    video_filepath=resource_copy_filepath,
                    session=session,
                    credentials_file=config.google_credentials_file,
                    bucket=config.validated_gcs_bucket_name,
                )

                # Split audio and store
                (audio_uri, local_audio_path,) = split_audio(
                    session_content_hash=session_content_hash,
                    tmp_video_filepath=tmp_video_filepath,
                    bucket=config.validated_gcs_bucket_name,
                    credentials_file=config.google_credentials_file,
                )

                # Check caption uri
                if session.caption_uri is not None:
                    # If the caption doesn't exist, remove the value
                    if not resource_exists(session.caption_uri):
                        log.warning(
                            f"File not found using provided caption URI: "
                            f"'{session.caption_uri}'. "
                            f"Removing the referenced caption URI."
                        )
                        session.caption_uri = None

                # Generate transcript
                transcript_uri, transcript = generate_transcript(
                    session_content_hash=session_content_hash,
                    audio_path=local_audio_path,
                    session=session,
                    bucket=config.validated_gcs_bucket_name,
                    credentials_file=config.google_credentials_file,
                    whisper_model_name=config.whisper_model_name,
                    whisper_model_confidence=config.whisper_model_confidence,
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
                resource_delete_task(
                    local_audio_path,
                    upstream_tasks=[transcript],
                )

                # Store all processed and provided data
                session_processing_results.append(
                    compile_session_processing_result(
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
def resource_copy_task(uri: str, dst: str = None, copy_suffix: bool = False) -> str:
    """
    Copy a file to a temporary location for processing.

    Parameters
    ----------
    uri: str
        The URI to the file to copy.
    dst: Optional[str]
        An optional destination path for the file.
        Default: None (place the file in the current directory with the same file name)
    copy_suffix: bool
        A bool for if the file suffix should be copied.
        Default: False

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
        dst=dst,
        copy_suffix=copy_suffix,
        overwrite=True,
    )


@task
def resource_delete_task(uri: str) -> None:
    """
    Remove local file.

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


@task(nout=3)
def convert_video_and_handle_host(
    video_filepath: str,
    session: Session,
    credentials_file: str,
    bucket: str,
) -> tuple[str, str, str]:
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

    trim_video = bool(session.video_start_time or session.video_end_time)

    # Convert to mp4 if file isn't of approved web format
    cdp_will_host = False
    if ext not in [".mp4", ".webm"]:
        cdp_will_host = True

        # Convert video to mp4
        mp4_filepath = file_utils.convert_video_to_mp4(
            video_filepath=Path(video_filepath),
            start_time=session.video_start_time,
            end_time=session.video_end_time,
        )

        fs_functions.remove_local_file(video_filepath)

        # Update variable name for easier downstream typing
        video_filepath = str(mp4_filepath)

    # host trimmed videos because it's simpler than setting
    # up transcription and playback ranges
    elif trim_video:
        cdp_will_host = True

        # Trim video
        trimmed_filepath = file_utils.clip_and_reformat_video(
            video_filepath=Path(video_filepath),
            start_time=session.video_start_time,
            end_time=session.video_end_time,
        )

        fs_functions.remove_local_file(video_filepath)

        # Update variable name for easier downstream typing
        video_filepath = str(trimmed_filepath)

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

    # Get unique session identifier
    session_content_hash = file_utils.hash_file_contents(uri=video_filepath)

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

    return video_filepath, hosted_video_media_url, session_content_hash


@task(nout=2)
def split_audio(
    session_content_hash: str,
    tmp_video_filepath: str,
    bucket: str,
    credentials_file: str,
) -> tuple[str, str]:
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
    audio_local_path: str
        The local path for the split audio.
    """
    # Check for existing audio
    local_audio_path = f"{session_content_hash}-audio.wav"
    audio_uri = fs_functions.get_file_uri(
        bucket=bucket,
        filename=local_audio_path,
        credentials_file=credentials_file,
    )

    # If no pre-existing audio, split
    if audio_uri is None:
        # Split and store the audio in temporary file prior to upload
        (
            local_audio_path,
            tmp_audio_log_out_filepath,
            tmp_audio_log_err_filepath,
        ) = file_utils.split_audio(
            video_read_path=tmp_video_filepath,
            audio_save_path=local_audio_path,
            overwrite=True,
        )

        # Store audio and logs
        audio_uri = fs_functions.upload_file(
            credentials_file=credentials_file,
            bucket=bucket,
            filepath=local_audio_path,
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
    # Download to ensure we have it for later
    else:
        local_audio_path = fs_functions.download_file(
            credentials_file=credentials_file,
            bucket=bucket,
            remote_filepath=local_audio_path,
            save_path=local_audio_path,
        )

    return audio_uri, local_audio_path


@task(max_retries=2, retry_delay=timedelta(seconds=10))
def use_speech_to_text_and_generate_transcript(
    audio_path: str,
    model_name: str = "medium",
    confidence: float | None = None,
) -> Transcript:
    """
    Pass the audio path to the speech recognition model.

    Parameters
    ----------
    audio_path: str
        The URI to the audio path. The audio must be on the local machine.
    model_name: str
        The whisper model to use for transcription.
    confidence: Optional[float]
        The confidence to set the produce transcript to.

    Returns
    -------
    transcript: Transcript
        The generated Transcript object.

    Notes
    -----
    See the sr_models.whisper.WhisperModel code for more details about
    pass through params.
    """
    # Init model
    model = WhisperModel(model_name=model_name, confidence=confidence)
    return model.transcribe(file_uri=audio_path)


@task(nout=2)
def finalize_and_archive_transcript(
    transcript: Transcript,
    transcript_save_path: str,
    bucket: str,
    credentials_file: str,
    session: Session,
) -> tuple[str, Transcript]:
    """
    Finalize and store the transcript to GCP.

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
        open_resource.write(transcript.to_json())

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
) -> tuple[str, str | None, Transcript | None, bool]:
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
            transcript = Transcript.from_json(open_resource.read())
    else:
        transcript = None

    return (tmp_transcript_filepath, transcript_uri, transcript, transcript_exists)


def generate_transcript(
    session_content_hash: str,
    audio_path: str,
    session: Session,
    bucket: str,
    credentials_file: str,
    whisper_model_name: str = "medium",
    whisper_model_confidence: float | None = None,
) -> tuple[str, Transcript]:
    """
    Route transcript generation to the correct processing.

    Parameters
    ----------
    session_content_hash: str
        The unique key (SHA256 hash of video content) for this session processing.
    audio_path: str
        The path to the audio file to generate a transcript from.
    session: Session
        The specific session details to be used in final transcript upload and
        archival.
    bucket: str
        The name of the GCS bucket to upload the produced audio to.
    credentials_file: str
        Path to the GCS JSON credentials file.
    whisper_model_name: str
        The whisper model to use for transcription.
    whisper_model_confidence: Optional[float]
        The confidence to set the produce transcript to.

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
        generated_transcript = use_speech_to_text_and_generate_transcript(
            audio_path=audio_path,
            model_name=whisper_model_name,
            confidence=whisper_model_confidence,
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

    return (result_transcript_uri, result_transcript)


@task(nout=2)
def generate_thumbnails(
    session_content_hash: str,
    tmp_video_path: str,
    event: EventIngestionModel,
    bucket: str,
    credentials_file: str,
) -> tuple[str, str]:
    """
    Create static and hover thumbnails.

    Parameters
    ----------
    session_content_hash: str
        The unique key (SHA256 hash of video content) for this session processing.
    tmp_video_path: str
        The URI to the video file to generate thumbnails from.
    event: EventIngestionModel
        The parent event of the session.
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


def _process_person_ingestion(  # noqa: C901
    person: ingestion_models.Person,
    default_session: Session,
    credentials_file: str,
    bucket: str,
    upload_cache: dict[str, db_models.Person] | None = None,
) -> db_models.Person:
    # The JSON string of the whole person tree turns out to be a great cache key because
    # 1. we can hash strings (which means we can shove them into a dictionary)
    # 2. the JSON string store all of the attached seat and role information
    # So, if the same person is referenced multiple times in the ingestion model
    # but most of those references have the same data and only a few have different data
    # the produced JSON string will note the differences and run when it needs to.

    # Create upload cache
    if upload_cache is None:
        upload_cache = {}

    person_cache_key = person.to_json()

    if person_cache_key not in upload_cache:
        # Store person picture file
        person_picture_db_model: db_models.File | None
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
            person_seat_image_db_model: db_models.File | None
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
                    person_role_body_db_model: db_models.Body | None
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
) -> bool | None:
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


@task(max_retries=2, retry_delay=timedelta(seconds=60))
def store_event_processing_results(  # noqa: C901
    event: EventIngestionModel,
    session_processing_results: list[SessionProcessingResult],
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
    processed_person_upload_cache: dict[str, db_models.Person] = {}
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
                matter_db_model = None

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
