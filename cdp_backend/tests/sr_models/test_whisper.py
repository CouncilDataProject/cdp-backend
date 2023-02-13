#!/usr/bin/env python

from pathlib import Path

import pytest
from rapidfuzz import fuzz

from cdp_backend.pipeline.transcript_model import Transcript
from cdp_backend.sr_models import WhisperModel


###############################################################################


@pytest.mark.parametrize(
    "audio_filename, expected_transcript_filename",
    [
        ("example_audio.wav", "example_whisper_output_transcript.json"),
        ("example-seattle-briefing.wav", "expected-seattle-briefing-transcript.json"),
    ],
)
def test_transcribe(
    resources_dir: Path, audio_filename: str, expected_transcript_filename: str
) -> None:
    # Get URIs and read
    file_uri = str((resources_dir / audio_filename).absolute())
    with open(resources_dir / expected_transcript_filename) as open_resource:
        expected = Transcript.from_json(open_resource.read())

    # Generate transcript
    model = WhisperModel(model_name="base")
    result = model.transcribe(file_uri)

    # Because ML is non-deterministic
    # we just check that the transcripts are similar
    expected_full_text = " ".join([sent.text for sent in expected.sentences])
    result_full_text = " ".join([sent.text for sent in result.sentences])
    similarity = fuzz.ratio(expected_full_text, result_full_text)
    assert similarity > 95
