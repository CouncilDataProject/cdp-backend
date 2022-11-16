#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import List, Optional
from unittest import mock
from unittest.mock import MagicMock

import pytest
from prefect import Flow

from cdp_backend.database import constants as db_constants
from cdp_backend.pipeline import event_gather_pipeline as pipeline
from cdp_backend.pipeline import ingestion_models
from cdp_backend.pipeline.ingestion_models import (
    EXAMPLE_FILLED_EVENT,
    EXAMPLE_MINIMAL_EVENT,
    EventIngestionModel,
    Session,
)
from cdp_backend.pipeline.mock_get_events import (
    FILLED_FLOW_CONFIG,
    MANY_FLOW_CONFIG,
    MINIMAL_FLOW_CONFIG,
    RANDOM_FLOW_CONFIG,
    _get_example_event,
)
from cdp_backend.pipeline.pipeline_config import EventGatherPipelineConfig
from cdp_backend.pipeline.transcript_model import EXAMPLE_TRANSCRIPT, Transcript

from ..conftest import EXAMPLE_M3U8_PLAYLIST_URI

#############################################################################

# NOTE:
# unittest mock patches are accesible in reverse order in params
# i.e. if we did the following patches
# @patch(module.func_a)
# @patch(module.func_b)
#
# the param order for the magic mocks would be
# def test_module(func_b, func_a):
#
# great system stdlib :upsidedownface:

PIPELINE_PATH = "cdp_backend.pipeline.event_gather_pipeline"
VIDEO_CONTENT_HASH = "7490ea6cf56648d60a40dd334e46e5d7de0f31dde0c7ce4d85747896fdd2ab42"

#############################################################################


@pytest.mark.parametrize(
    "config",
    [FILLED_FLOW_CONFIG, MANY_FLOW_CONFIG, MINIMAL_FLOW_CONFIG, RANDOM_FLOW_CONFIG],
)
def test_create_event_gather_flow(config: EventGatherPipelineConfig) -> None:
    flow = pipeline.create_event_gather_flow(config=config)
    assert isinstance(flow, Flow)


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Path handling / splitting failing due to windows path separator",
)
@mock.patch(f"{PIPELINE_PATH}.fs_functions.get_file_uri")
@mock.patch(f"{PIPELINE_PATH}.fs_functions.upload_file")
@pytest.mark.parametrize(
    "get_file_uri_value, audio_upload_file_return",
    [
        (
            None,
            f"fake://{VIDEO_CONTENT_HASH}-audio.wav",
        ),
        (
            f"fake://{VIDEO_CONTENT_HASH}-audio.wav",
            f"fake://{VIDEO_CONTENT_HASH}-audio.wav",
        ),
    ],
)
def test_split_audio(
    mock_upload_file: MagicMock,
    mock_get_file_uri: MagicMock,
    get_file_uri_value: str,
    audio_upload_file_return: str,
    example_video: Path,
) -> None:
    mock_get_file_uri.return_value = get_file_uri_value
    mock_upload_file.return_value = audio_upload_file_return

    audio_uri = pipeline.split_audio.run(
        session_content_hash=VIDEO_CONTENT_HASH,
        tmp_video_filepath=str(example_video),
        bucket="bucket",
        credentials_file="/fake/credentials/path",
    )

    # Check outputs
    assert audio_uri == audio_upload_file_return

    # Cleanup
    for suffix in ["err", "out", "wav"]:
        gen_test_file = Path(f"{VIDEO_CONTENT_HASH}-audio.{suffix}")
        if gen_test_file.exists():
            os.remove(gen_test_file)


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Path handling / splitting failing due to windows path separator",
)
@mock.patch(f"{PIPELINE_PATH}.fs_functions.upload_file")
@pytest.mark.parametrize(
    "example_static_thumbnail_url, example_hover_thumbnail_url,"
    "example_session_content_hash, event",
    [
        (
            f"fake://{VIDEO_CONTENT_HASH}-static-thumbnail.png",
            f"fake://{VIDEO_CONTENT_HASH}-hover-thumbnail.gif",
            VIDEO_CONTENT_HASH,
            deepcopy(EXAMPLE_MINIMAL_EVENT),
        ),
    ],
)
def test_generate_thumbnails(
    mock_upload_file: MagicMock,
    example_static_thumbnail_url: str,
    example_hover_thumbnail_url: str,
    example_session_content_hash: str,
    event: EventIngestionModel,
    example_video: Path,
) -> None:
    # Since mock_upload_file only allows for one return value and since the real
    # thumbnail generator calls upload_file twice, it is necessary to test each
    # thumbnail generation process separately
    mock_upload_file.side_effect = [
        example_static_thumbnail_url,
        example_hover_thumbnail_url,
    ]
    (static_thumbnail_url, hover_thumbnail_url,) = pipeline.generate_thumbnails.run(
        session_content_hash=example_session_content_hash,
        tmp_video_path=str(example_video),
        event=event,
        bucket="bucket",
        credentials_file="/fake/credentials/path",
    )

    # Check outputs
    assert static_thumbnail_url == example_static_thumbnail_url
    assert hover_thumbnail_url == example_hover_thumbnail_url

    # Cleanup
    for suffix in ["hover-thumbnail.gif", "static-thumbnail.png"]:
        gen_test_file = Path(f"{VIDEO_CONTENT_HASH}-{suffix}")
        if gen_test_file.exists():
            os.remove(gen_test_file)


@pytest.mark.parametrize(
    "event, expected_phrases",
    [
        (deepcopy(EXAMPLE_MINIMAL_EVENT), ["Full Council"]),
        (
            deepcopy(EXAMPLE_FILLED_EVENT),
            # Note: the order here is because under the hood, we are using a set and
            # casting to a list.
            # It's the item addition order that matters, not the order of the phrases
            # So this is completely fine
            [
                "AN ORDINANCE relating to the financing of the West Seattle Bridge",
                "Teresa Mosqueda",
                "Andrew Lewis",
                "Inf 1656",
                "Full Council",
                "M. Lorena González",
                "Chair",
                "Alex Pedersen",
                "Council President",
                "CB 119858",
                "Vice Chair",
            ],
        ),
    ],
)
def test_construct_speech_to_text_phrases_context(
    event: EventIngestionModel, expected_phrases: List[str]
) -> None:
    phrases = pipeline.construct_speech_to_text_phrases_context.run(
        event,
    )

    assert set(phrases) == set(expected_phrases)


# Set up a session with the local captions file instead of a remote captions file
# to ensure that no random errors happen to due remote service interruption
LOCAL_CAPTIONS_SESSION = deepcopy(EXAMPLE_FILLED_EVENT.sessions[1])
LOCAL_CAPTIONS_SESSION.caption_uri = str(
    (Path(__file__).parent.parent / "resources" / "fake_caption.vtt").absolute()
)


@mock.patch(f"{PIPELINE_PATH}.fs_functions.get_file_uri")
@mock.patch(f"{PIPELINE_PATH}.use_speech_to_text_and_generate_transcript.run")
@mock.patch(f"{PIPELINE_PATH}.fs_functions.upload_file")
@pytest.mark.parametrize(
    "mock_speech_to_text_return, "
    "mock_upload_transcript_return, "
    "session, "
    "event",
    [
        # Testing no captions case
        (
            EXAMPLE_TRANSCRIPT,
            "ex://abc123-transcript.json",
            deepcopy(EXAMPLE_MINIMAL_EVENT.sessions[0]),
            deepcopy(EXAMPLE_MINIMAL_EVENT),
        ),
        # Testing captions case
        (
            None,
            "ex://abc123-transcript.json",
            deepcopy(LOCAL_CAPTIONS_SESSION),
            deepcopy(EXAMPLE_FILLED_EVENT),
        ),
    ],
)
@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="local caption path handling for windows",
)
def test_generate_transcript(
    mock_upload_transcript: MagicMock,
    mock_speech_to_text: MagicMock,
    mock_get_transcript_uri: MagicMock,
    mock_speech_to_text_return: Transcript,
    mock_upload_transcript_return: str,
    session: Session,
    event: EventIngestionModel,
) -> None:
    mock_get_transcript_uri.return_value = None
    mock_speech_to_text.return_value = mock_speech_to_text_return
    mock_upload_transcript.return_value = mock_upload_transcript_return

    with Flow("Test Generate Transcript") as flow:
        pipeline.generate_transcript(
            session_content_hash="abc123",
            audio_uri="fake://doesn't-matter.wav",
            session=session,
            event=event,
            bucket="bucket",
            credentials_file="fake/creds.json",
        )

    # Run the flow
    state = flow.run()

    # Check state and results
    assert state.is_successful()


example_person = ingestion_models.Person(name="Bob Boberson")
example_minutes_item = ingestion_models.MinutesItem(name="Definitely happened")
failed_events_minutes_item = ingestion_models.EventMinutesItem(
    minutes_item=example_minutes_item,
    decision=db_constants.EventMinutesItemDecision.FAILED,
)
passed_events_minutes_item = ingestion_models.EventMinutesItem(
    minutes_item=example_minutes_item,
    decision=db_constants.EventMinutesItemDecision.PASSED,
)


@pytest.mark.parametrize(
    "vote, event_minutes_item, expected",
    [
        # The minutes item passed
        # They approved or approved-by-abstention-or-absense
        (
            ingestion_models.Vote(
                person=example_person,
                decision=db_constants.VoteDecision.APPROVE,
            ),
            passed_events_minutes_item,
            True,
        ),
        (
            ingestion_models.Vote(
                person=example_person,
                decision=db_constants.VoteDecision.ABSTAIN_APPROVE,
            ),
            passed_events_minutes_item,
            True,
        ),
        (
            ingestion_models.Vote(
                person=example_person,
                decision=db_constants.VoteDecision.ABSENT_APPROVE,
            ),
            passed_events_minutes_item,
            True,
        ),
        # They rejected or rejected-by-abstention-or-absense
        (
            ingestion_models.Vote(
                person=example_person,
                decision=db_constants.VoteDecision.REJECT,
            ),
            passed_events_minutes_item,
            False,
        ),
        (
            ingestion_models.Vote(
                person=example_person,
                decision=db_constants.VoteDecision.ABSTAIN_REJECT,
            ),
            passed_events_minutes_item,
            False,
        ),
        (
            ingestion_models.Vote(
                person=example_person,
                decision=db_constants.VoteDecision.ABSENT_REJECT,
            ),
            passed_events_minutes_item,
            False,
        ),
        # The minutes item failed
        # They approved or approved-by-abstention-or-absense
        (
            ingestion_models.Vote(
                person=example_person,
                decision=db_constants.VoteDecision.APPROVE,
            ),
            failed_events_minutes_item,
            False,
        ),
        (
            ingestion_models.Vote(
                person=example_person,
                decision=db_constants.VoteDecision.ABSTAIN_APPROVE,
            ),
            failed_events_minutes_item,
            False,
        ),
        (
            ingestion_models.Vote(
                person=example_person,
                decision=db_constants.VoteDecision.ABSENT_APPROVE,
            ),
            failed_events_minutes_item,
            False,
        ),
        # They rejected or rejected-by-abstention-or-absense
        (
            ingestion_models.Vote(
                person=example_person,
                decision=db_constants.VoteDecision.REJECT,
            ),
            failed_events_minutes_item,
            True,
        ),
        (
            ingestion_models.Vote(
                person=example_person,
                decision=db_constants.VoteDecision.ABSTAIN_REJECT,
            ),
            failed_events_minutes_item,
            True,
        ),
        (
            ingestion_models.Vote(
                person=example_person,
                decision=db_constants.VoteDecision.ABSENT_REJECT,
            ),
            failed_events_minutes_item,
            True,
        ),
        # The minutes item passed
        # They were a non-voting member
        (
            ingestion_models.Vote(
                person=example_person,
                decision=db_constants.VoteDecision.ABSTAIN_NON_VOTING,
            ),
            passed_events_minutes_item,
            None,
        ),
        (
            ingestion_models.Vote(
                person=example_person,
                decision=db_constants.VoteDecision.ABSENT_NON_VOTING,
            ),
            passed_events_minutes_item,
            None,
        ),
        # The minutes item failed
        # They were a non-voting member
        (
            ingestion_models.Vote(
                person=example_person,
                decision=db_constants.VoteDecision.ABSTAIN_NON_VOTING,
            ),
            failed_events_minutes_item,
            None,
        ),
        (
            ingestion_models.Vote(
                person=example_person,
                decision=db_constants.VoteDecision.ABSENT_NON_VOTING,
            ),
            failed_events_minutes_item,
            None,
        ),
    ],
)
def test_calculate_in_majority(
    vote: ingestion_models.Vote,
    event_minutes_item: ingestion_models.EventMinutesItem,
    expected: Optional[bool],
) -> None:
    actual = pipeline._calculate_in_majority(
        vote=vote,
        event_minutes_item=event_minutes_item,
    )
    assert actual == expected


###############################################################################
# Database storage tests prep

# Generate random events and construct session processing results for each
# While we can't guarentee this will cover all cases,
# this should cover most cases.

RANDOM_EVENTS_AND_PROC_RESULTS = []
for i in range(6):
    rand_event = _get_example_event()
    proc_results = []
    for session in rand_event.sessions:
        proc_results.append(
            pipeline.SessionProcessingResult(
                session=session,
                session_video_hosted_url="fake://doesnt-matter.mp4",
                session_content_hash="fakehash123",
                audio_uri="fake://doesnt-matter.wav",
                transcript=EXAMPLE_TRANSCRIPT,
                transcript_uri="fake://doesnt-matter-transcript.json",
                static_thumbnail_uri="fake://doesnt-matter-static-thumbnail.png",
                hover_thumbnail_uri="fake://doesnt-matter-hover-thumbnail.gif",
            )
        )

    # Append rand event and proce results as tuple
    # Set fail_file_uploads to even param sets
    RANDOM_EVENTS_AND_PROC_RESULTS.append((rand_event, proc_results, i % 2 == 0, False))

###############################################################################


@mock.patch(f"{PIPELINE_PATH}.file_utils.resource_copy")
@mock.patch(f"{PIPELINE_PATH}.fs_functions.upload_file")
@mock.patch(f"{PIPELINE_PATH}.fs_functions.remove_local_file")
@mock.patch(f"{PIPELINE_PATH}.db_functions.upload_db_model")
@pytest.mark.parametrize(
    "event, session_processing_results, fail_file_uploads, fail_try_url",
    [
        (
            deepcopy(EXAMPLE_MINIMAL_EVENT),
            [
                pipeline.SessionProcessingResult(
                    session=deepcopy(EXAMPLE_MINIMAL_EVENT.sessions[0]),
                    session_video_hosted_url="fake://doesnt-matter.mp4",
                    session_content_hash="fakehash123",
                    audio_uri="ex://abc123-audio.wav",
                    transcript=EXAMPLE_TRANSCRIPT,
                    transcript_uri="ex://abc123-transcript.json",
                    static_thumbnail_uri="ex://abc123-static-thumbnail.png",
                    hover_thumbnail_uri="ex://abc123-hover-thumbnail.gif",
                ),
            ],
            False,
            False,
        ),
        (
            deepcopy(EXAMPLE_FILLED_EVENT),
            [
                pipeline.SessionProcessingResult(
                    session=deepcopy(EXAMPLE_FILLED_EVENT.sessions[0]),
                    session_video_hosted_url="fake://doesnt-matter-1.mp4",
                    session_content_hash="fakehash123",
                    audio_uri="ex://abc123-audio.wav",
                    transcript=EXAMPLE_TRANSCRIPT,
                    transcript_uri="ex://abc123-transcript.json",
                    static_thumbnail_uri="ex://abc123-static-thumbnail.png",
                    hover_thumbnail_uri="ex://abc123-hover-thumbnail.gif",
                ),
                pipeline.SessionProcessingResult(
                    session=deepcopy(EXAMPLE_FILLED_EVENT.sessions[1]),
                    session_video_hosted_url="fake://doesnt-matter-2.mp4",
                    session_content_hash="fakehash1234",
                    audio_uri="ex://def456-audio.wav",
                    transcript=EXAMPLE_TRANSCRIPT,
                    transcript_uri="ex://def456-transcript.json",
                    static_thumbnail_uri="ex://def456-static-thumbnail.png",
                    hover_thumbnail_uri="ex://def456-hover-thumbnail.gif",
                ),
            ],
            False,
            False,
        ),
        (
            deepcopy(EXAMPLE_FILLED_EVENT),
            [],
            False,
            True,
        ),
        (
            deepcopy(EXAMPLE_FILLED_EVENT),
            [],
            False,
            False,
        ),
        *RANDOM_EVENTS_AND_PROC_RESULTS,
    ],
)
def test_store_event_processing_results(
    mock_upload_db_model: MagicMock,
    mock_remove_local_file: MagicMock,
    mock_upload_file: MagicMock,
    mock_resource_copy: MagicMock,
    event: EventIngestionModel,
    session_processing_results: List[pipeline.SessionProcessingResult],
    fail_file_uploads: bool,
    fail_try_url: bool,
) -> None:
    # All of the resource copies relate to image file uploads / archival.
    # But we aren't actually uploading so just make sure that we aren't downloading
    # externally either.
    mock_resource_copy.return_value = "doesnt-matter.ext"

    with mock.patch(f"{PIPELINE_PATH}.try_url") as mock_resource_exists:
        if fail_try_url:
            mock_resource_exists.side_effect = LookupError()
        else:
            mock_resource_exists.return_value = True

        # Set file upload side effect
        if fail_file_uploads:
            mock_upload_file.side_effect = FileNotFoundError()

        pipeline.store_event_processing_results.run(
            event=event,
            session_processing_results=session_processing_results,
            credentials_file="fake/credentials.json",
            bucket="doesnt://matter",
        )


NONSECURE_VIDEO_MINIMAL_EVENT_BUT_SECURE_FINDABLE = deepcopy(EXAMPLE_MINIMAL_EVENT)
NONSECURE_VIDEO_MINIMAL_EVENT_BUT_SECURE_FINDABLE.sessions[
    0
].video_uri = NONSECURE_VIDEO_MINIMAL_EVENT_BUT_SECURE_FINDABLE.sessions[
    0
].video_uri.replace(
    "https://", "http://"
)

NON_EXISTENT_REMOTE_MINIMAL_EVENT = deepcopy(EXAMPLE_MINIMAL_EVENT)
NON_EXISTENT_REMOTE_MINIMAL_EVENT.sessions[
    0
].video_uri = "s3://bucket/does-not-exist.txt"

EXISTING_REMOTE_M3U8_MINIMAL_EVENT = deepcopy(EXAMPLE_MINIMAL_EVENT)
EXISTING_REMOTE_M3U8_MINIMAL_EVENT.sessions[0].video_uri = EXAMPLE_M3U8_PLAYLIST_URI


@mock.patch(f"{PIPELINE_PATH}.fs_functions.upload_file")
@mock.patch(f"{PIPELINE_PATH}.fs_functions.get_open_url_for_gcs_file")
@mock.patch(f"{PIPELINE_PATH}.fs_functions.remove_local_file")
@mock.patch(f"{PIPELINE_PATH}.file_utils.convert_video_to_mp4")
@pytest.mark.parametrize(
    "video_filepath, session, expected_filepath, expected_hosted_video_url",
    [
        (
            "example_video.mkv",
            deepcopy(EXAMPLE_MINIMAL_EVENT.sessions[0]),
            "example_video.mp4",
            "hosted-video.mp4",
        ),
        (
            "example_video.mp4",
            deepcopy(EXAMPLE_MINIMAL_EVENT.sessions[0]),
            "example_video.mp4",
            EXAMPLE_MINIMAL_EVENT.sessions[0].video_uri,
        ),
        (
            "example_video.mp4",
            deepcopy(NONSECURE_VIDEO_MINIMAL_EVENT_BUT_SECURE_FINDABLE.sessions[0]),
            "example_video.mp4",
            EXAMPLE_MINIMAL_EVENT.sessions[0].video_uri,
        ),
        (
            "example_video.mp4",
            deepcopy(NON_EXISTENT_REMOTE_MINIMAL_EVENT.sessions[0]),
            "example_video.mp4",
            "hosted-video.mp4",
        ),
        (
            "example_video.mp4",
            deepcopy(EXISTING_REMOTE_M3U8_MINIMAL_EVENT.sessions[0]),
            "example_video.mp4",
            "hosted-video.mp4",
        ),
    ],
)
def test_convert_video_and_handle_host(
    mock_convert_video_to_mp4: MagicMock,
    mock_remove_local_file: MagicMock,
    mock_generate_url: MagicMock,
    mock_upload_file: MagicMock,
    video_filepath: str,
    session: Session,
    expected_filepath: str,
    expected_hosted_video_url: str,
) -> None:
    mock_upload_file.return_value = "file_store_uri"
    mock_generate_url.return_value = "hosted-video.mp4"
    mock_convert_video_to_mp4.return_value = expected_filepath

    (
        mp4_filepath,
        session_video_hosted_url,
    ) = pipeline.convert_video_and_handle_host.run(
        session_content_hash="abc123",
        video_filepath=video_filepath,
        session=session,
        credentials_file="fake/credentials.json",
        bucket="doesnt://matter",
    )

    # Make sure mp4 files don't go through conversion
    if Path(video_filepath).suffix == ".mp4":
        assert not mock_convert_video_to_mp4.called

    assert mp4_filepath == expected_filepath
    assert session_video_hosted_url == expected_hosted_video_url
