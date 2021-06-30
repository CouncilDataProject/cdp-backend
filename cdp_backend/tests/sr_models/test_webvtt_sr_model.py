#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

import pytest

from cdp_backend.pipeline.transcript_model import Transcript
from cdp_backend.sr_models import WebVTTSRModel


@pytest.mark.parametrize(
    "webvtt_filename, expected_filename",
    [("fake_caption.vtt", "generated_transcript_from_webvtt.json")],
)
def test_transcribe(
    resources_dir: Path, webvtt_filename: str, expected_filename: str
) -> None:
    # Get URIs and read
    file_uri = str((resources_dir / webvtt_filename).absolute())
    with open(resources_dir / expected_filename) as open_resource:
        expected = Transcript.from_json(open_resource.read())  # type: ignore

    # Generate transcript
    model = WebVTTSRModel()
    result = model.transcribe(file_uri)

    # Remove created datetimes
    result.created_datetime = None  # type: ignore
    expected.created_datetime = None

    assert result == expected
