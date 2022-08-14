#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cdp_backend.pipeline.transcript_model import EXAMPLE_TRANSCRIPT, Transcript

###############################################################################


def test_model_serdes() -> None:
    example_transcript_str = EXAMPLE_TRANSCRIPT.to_json()
    example_transcript_des = Transcript.from_json(example_transcript_str)

    assert EXAMPLE_TRANSCRIPT == example_transcript_des
