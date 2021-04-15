#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
from unittest.mock import Mock
from typing import Any, List
from py._path.local import LocalPath

import pytest
from requests import RequestException
from webvtt.structures import Caption

from cdp_backend.sr_models.webvtt_sr_model import WebVTTSRModel


@pytest.fixture
def fake_caption(data_dir: Path) -> Path:
    return data_dir / "fake_caption.vtt"


@pytest.fixture
def example_webvtt_sr_model() -> WebVTTSRModel:
    webvtt_sr_model = WebVTTSRModel("&gt;")
    return webvtt_sr_model


# Check whether WebVTTSRModel raise an RequestException if the uri of caption file is
# invalid
def test_webvtt_sr_model_request_caption_content(example_webvtt_sr_model: WebVTTSRModel) -> None:
    with pytest.raises(RequestException):
        example_webvtt_sr_model._request_caption_content("invalid-caption-uri")


@pytest.mark.parametrize(
    "captions, expected",
    [
        (
            [
                Caption(text="&gt;&gt; Start of Dialog 1."),
                Caption(text="End of Dialog 1."),
                Caption(text="&gt;&gt; [ APPLAUSE ]"),
                Caption(text="&gt;&gt; Dialog 2."),
            ],
            [
                ["Start of Dialog 1.", "End of Dialog 1."],
                ["[ APPLAUSE ]"],
                ["Dialog 2."],
            ],
        ),
        (
            [
                Caption(text="&gt;&gt; Dialog 1."),
                Caption(text="&gt;&gt; [ ROLL BEING CALLED ]"),
                Caption(text="&gt;&gt; Dialog 2."),
            ],
            [["Dialog 1."], ["[ ROLL BEING CALLED ]"], ["Dialog 2."]],
        ),
        (
            [
                Caption(text="&gt;&gt; [ LAUGHTER ] Dialog 1."),
                Caption(text="&gt;&gt; [ APPLAUSE ]"),
                Caption(text="&gt;&gt; Dialog 2."),
            ],
            [["[ LAUGHTER ] Dialog 1."], ["[ APPLAUSE ]"], ["Dialog 2."]],
        ),
        (
            [
                Caption(text="&gt;&gt; Sentence"),
                Caption(text="one."),
                Caption(text="&gt;&gt; Sentence"),
                Caption(text="two!"),
                Caption(text="Sentence"),
                Caption(text="three!"),
                Caption(text="Sentence"),
                Caption(text="four?"),
            ],
            [["Sentence one."], ["Sentence two!", "Sentence three!", "Sentence four?"]],
        ),
        (
            [
                Caption(text="&gt;&gt; Sentence"),
                Caption(text="one, no sentence ending punctuation"),
                Caption(text="&gt;&gt; Sentence"),
                Caption(text="two."),
            ],
            [["Sentence one, no sentence ending punctuation"], ["Sentence two."]],
        ),
        (
            [Caption(text="Sentence one."), Caption(text="ú&gt;&gt; Sentence two.")],
            [["Sentence one."], ["Sentence two."]],
        ),
    ],
)
def test_webvtt_sr_model_create_timestamped_speaker_turns(
    captions: List[Caption], expected: Any, example_webvtt_sr_model: WebVTTSRModel
) -> None:
    speaker_turns = example_webvtt_sr_model._get_speaker_turns(captions)
    ts_speaker_turns = example_webvtt_sr_model._create_timestamped_speaker_turns(
        speaker_turns
    )
    # Check if the number of speaker turns is correct
    assert len(ts_speaker_turns) == len(expected)
    for i, speaker_turn in enumerate(expected):
        # Check if the number of sentences per speaker turn is correct
        assert len(ts_speaker_turns[i]["data"]) == len(speaker_turn)
        # Check if sentence string matches expected sentence string
        for j, sentence in enumerate(speaker_turn):
            assert ts_speaker_turns[i]["data"][j]["text"] == sentence  #type: ignore


def test_webvtt_sr_model_transcribe(example_webvtt_sr_model: WebVTTSRModel, fake_caption: Caption, tmpdir: LocalPath) -> None:
    with open(fake_caption, "r") as fake_caption_file:
        caption_text = fake_caption_file.read()

    example_webvtt_sr_model._request_caption_content = Mock(return_value=caption_text)  # type: ignore

    example_webvtt_sr_model.transcribe(
        "any-caption-uri",
        raw_transcript_save_path=tmpdir / "raw.json",
        timestamped_sentences_save_path=tmpdir / "timestamped_sentences.json",
        timestamped_speaker_turns_save_path=tmpdir / "timestamped_speaker_turns.json",
    )
