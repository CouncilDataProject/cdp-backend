#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from pathlib import Path
from typing import List
from unittest import mock
from unittest.mock import MagicMock

import pytest
from prefect import Flow

from cdp_backend.pipeline import event_gather_pipeline as pipeline
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


@mock.patch(f"{PIPELINE_PATH}.db_functions.upload_db_model")
@pytest.mark.parametrize(
    "event, session_processing_results",
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
        ),
    ],
)
def test_store_event_processing_results(
    mock_upload_db_model: MagicMock,
    event: EventIngestionModel,
    session_processing_results: List[pipeline.SessionProcessingResult],
) -> None:
    pipeline.store_event_processing_results.run(  # type: ignore
        event=event,
        session_processing_results=session_processing_results,
        credentials_file="fake/credentials.json",
    )
