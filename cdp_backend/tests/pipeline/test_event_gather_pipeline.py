#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
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
    "get_file_uri_value, audio_upload_file_return, expected_session_content_hash",
    [
        (
            None,
            f"fake://{VIDEO_CONTENT_HASH}-audio.wav",
            VIDEO_CONTENT_HASH,
        ),
        (
            f"fake://{VIDEO_CONTENT_HASH}-audio.wav",
            f"fake://{VIDEO_CONTENT_HASH}-audio.wav",
            VIDEO_CONTENT_HASH,
        ),
    ],
)
def test_get_video_and_split_audio(
    mock_upload_file: MagicMock,
    mock_get_file_uri: MagicMock,
    get_file_uri_value: str,
    audio_upload_file_return: str,
    expected_session_content_hash: str,
    example_video: Path,
) -> None:
    mock_get_file_uri.return_value = get_file_uri_value
    mock_upload_file.return_value = audio_upload_file_return

    (
        session_content_hash,
        audio_uri,
    ) = pipeline.get_video_and_split_audio.run(  # type: ignore
        video_uri=str(example_video),
        bucket="bucket",
        credentials_file="/fake/credentials/path",
    )

    # Check outputs
    assert session_content_hash == expected_session_content_hash
    assert audio_uri == audio_upload_file_return


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Path handling / splitting failing due to windows path separator",
)
@mock.patch(f"{PIPELINE_PATH}.fs_functions.upload_file")
@pytest.mark.parametrize(
    "example_static_thumbnail_url, example_hover_thumbnail_url,"
    "example_session_content_hash, event, is_static",
    [
        (
            f"fake://{VIDEO_CONTENT_HASH}-static-thumbnail.png",
            f"fake://{VIDEO_CONTENT_HASH}-hover-thumbnail.gif",
            VIDEO_CONTENT_HASH,
            EXAMPLE_MINIMAL_EVENT,
            True,
        ),
        (
            f"fake://{VIDEO_CONTENT_HASH}-static-thumbnail.png",
            f"fake://{VIDEO_CONTENT_HASH}-hover-thumbnail.gif",
            VIDEO_CONTENT_HASH,
            EXAMPLE_MINIMAL_EVENT,
            False,
        ),
    ],
)
def test_get_video_and_generate_thumbnails(
    mock_upload_file: MagicMock,
    # mock_get_file_uri: MagicMock,
    example_static_thumbnail_url: str,
    example_hover_thumbnail_url: str,
    example_session_content_hash: str,
    event: EventIngestionModel,
    is_static: bool,
    example_video: Path,
) -> None:
    # Since mock_upload_file only allows for one return value and since the real
    # thumbnail generator calls upload_file twice, it is necessary to test each
    # thumbnail generation process separately
    if is_static:
        mock_upload_file.return_value = example_static_thumbnail_url
    else:
        mock_upload_file.return_value = example_hover_thumbnail_url

    (
        static_thumbnail_url,
        hover_thumbnail_url,
    ) = pipeline.get_video_and_generate_thumbnails.run(  # type: ignore
        session_content_hash=example_session_content_hash,
        video_uri=str(example_video),
        event=event,
        bucket="bucket",
        credentials_file="/fake/credentials/path",
    )

    # Check outputs
    if is_static:
        assert static_thumbnail_url == example_static_thumbnail_url
    else:
        assert hover_thumbnail_url == example_hover_thumbnail_url


@pytest.mark.parametrize(
    "event, expected_phrases",
    [
        (EXAMPLE_MINIMAL_EVENT, ["Full Council"]),
        (
            EXAMPLE_FILLED_EVENT,
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
    phrases = pipeline.construct_speech_to_text_phrases_context.run(  # type: ignore
        event,
    )

    assert set(phrases) == set(expected_phrases)


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
            EXAMPLE_MINIMAL_EVENT.sessions[0],
            EXAMPLE_MINIMAL_EVENT,
        ),
        # Testing captions case
        (
            None,
            "ex://abc123-transcript.json",
            EXAMPLE_FILLED_EVENT.sessions[1],
            EXAMPLE_FILLED_EVENT,
        ),
    ],
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
    assert state.is_successful()  # type: ignore


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
                audio_uri="fake://doesnt-matter.wav",
                transcript=EXAMPLE_TRANSCRIPT,
                transcript_uri="fake://doesnt-matter-transcript.json",
                static_thumbnail_uri="fake://doesnt-matter-static-thumbnail.png",
                hover_thumbnail_uri="fake://doesnt-matter-hover-thumbnail.gif",
            )
        )

    # Append rand event and proce results as tuple
    # Set fail_file_uploads to even param sets
    RANDOM_EVENTS_AND_PROC_RESULTS.append((rand_event, proc_results, i % 2 == 0))

###############################################################################


@mock.patch(f"{PIPELINE_PATH}.file_utils.resource_copy")
@mock.patch(f"{PIPELINE_PATH}.fs_functions.upload_file")
@mock.patch(f"{PIPELINE_PATH}.fs_functions.remove_local_file")
@mock.patch(f"{PIPELINE_PATH}.db_functions.upload_db_model")
@pytest.mark.parametrize(
    "event, session_processing_results, fail_file_uploads",
    [
        (
            EXAMPLE_MINIMAL_EVENT,
            [
                pipeline.SessionProcessingResult(
                    session=EXAMPLE_MINIMAL_EVENT.sessions[0],
                    audio_uri="ex://abc123-audio.wav",
                    transcript=EXAMPLE_TRANSCRIPT,
                    transcript_uri="ex://abc123-transcript.json",
                    static_thumbnail_uri="ex://abc123-static-thumbnail.png",
                    hover_thumbnail_uri="ex://abc123-hover-thumbnail.gif",
                ),
            ],
            False,
        ),
        (
            EXAMPLE_FILLED_EVENT,
            [
                pipeline.SessionProcessingResult(
                    session=EXAMPLE_FILLED_EVENT.sessions[0],
                    audio_uri="ex://abc123-audio.wav",
                    transcript=EXAMPLE_TRANSCRIPT,
                    transcript_uri="ex://abc123-transcript.json",
                    static_thumbnail_uri="ex://abc123-static-thumbnail.png",
                    hover_thumbnail_uri="ex://abc123-hover-thumbnail.gif",
                ),
                pipeline.SessionProcessingResult(
                    session=EXAMPLE_FILLED_EVENT.sessions[1],
                    audio_uri="ex://def456-audio.wav",
                    transcript=EXAMPLE_TRANSCRIPT,
                    transcript_uri="ex://def456-transcript.json",
                    static_thumbnail_uri="ex://def456-static-thumbnail.png",
                    hover_thumbnail_uri="ex://def456-hover-thumbnail.gif",
                ),
            ],
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
) -> None:
    # All of the resource copies relate to image file uploads / archival.
    # But we aren't actually uploading so just make sure that we aren't downloading
    # externally either.
    mock_resource_copy.return_value = "doesnt-matter.ext"

    # Set file upload side effect
    if fail_file_uploads:
        mock_upload_file.side_effect = FileNotFoundError()

    pipeline.store_event_processing_results.run(  # type: ignore
        event=event,
        session_processing_results=session_processing_results,
        credentials_file="fake/credentials.json",
        bucket="doesnt://matter",
    )
