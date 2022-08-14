#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

import pytest

from cdp_backend.pipeline.transcript_model import Transcript
from cdp_backend.sr_models import WebVTTSRModel


@pytest.mark.parametrize(
    "webvtt_filename, expected_filename",
    [
        ("fake_caption.vtt", "generated_transcript_from_fake_captions.json"),
        (
            "brief_080221_2012161.vtt",
            "generated_transcript_from_brief_080221_2012161.json",
        ),
        ("boston_captions.vtt", "boston_transcript.json"),
    ],
)
def test_transcribe(
    resources_dir: Path, webvtt_filename: str, expected_filename: str
) -> None:
    # Get URIs and read
    file_uri = str((resources_dir / webvtt_filename).absolute())
    with open(resources_dir / expected_filename) as open_resource:
        expected = Transcript.from_json(open_resource.read())

    # Generate transcript
    model = WebVTTSRModel()
    result = model.transcribe(file_uri)

    # Because floating point math is hard and sometimes not exactly the same
    # just compare the text
    for sentence_index, sentence in enumerate(result.sentences):
        for word_index, word in enumerate(sentence.words):
            assert (
                word.text == expected.sentences[sentence_index].words[word_index].text
            )

        assert sentence.text == expected.sentences[sentence_index].text
