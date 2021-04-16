#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Dict, List, Union

# Transcript data json blobs will look like the following
# [{"start_time": 0.0, "portion": "Hello world!", "end_time": 2.1}, ...]
TranscriptDataJSON = List[Dict[str, Union[str, float]]]


class TranscriptFormats:
    raw = "raw"
    timestamped_words = "timestamped-words"
    timestamped_sentences = "timestamped-sentences"
    timestamped_speaker_turns = "timestamped-speaker-turns"
