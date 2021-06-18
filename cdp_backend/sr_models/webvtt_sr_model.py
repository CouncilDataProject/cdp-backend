#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Union

import fsspec
import nltk
import truecase
import webvtt

from ..pipeline.transcript_model import Sentence, Transcript, Word
from .sr_model import SRModel

###############################################################################

log = logging.getLogger(__name__)

###############################################################################


class WebVTTSRModel(SRModel):
    def __init__(
        self,
        new_turn_pattern: str = "&gt;",
        confidence: float = 1.0,
        **kwargs: Any,
    ):
        # New speaker turn must begin with one or more new_turn_pattern str
        # This will create a regex pattern to allow for one or more of the pattern
        self.new_turn_pattern = r"({})+\s*(.+)$".format(new_turn_pattern)

        # Sentence must be ended by period, question mark, or exclamation point.
        # (or a new speaker starts)
        self.end_of_sentence_pattern = r"^.+[.?!]\s*$"

        # Confidence is tricky. We allow it to be a parameter because closed captions
        # aren't always 100% accurate. For Seattle, I would guess they are about 97%
        # accurate.
        self.confidence = confidence

    def _normalize_text(self, text: str) -> str:
        normalized_text = truecase.get_true_case(text)

        # Fix some punctuation issue, e.g. `roughly$ 19` bececomes `roughly $19`
        normalized_text = re.sub(
            r"([#$(<[{]) ", lambda x: f" {x.group(1)}", normalized_text
        )
        return normalized_text

    def transcribe(self, file_uri: Union[str, Path], **kwargs: Any) -> Transcript:
        # Download punkt for truecase module
        nltk.download("punkt")

        # Read the caption file
        with fsspec.open(file_uri, "rb") as open_resource:
            captions = webvtt.read(open_resource)

        # Keep track of current speaker caption collection
        all_speaker_captions = []
        current_speaker_captions: Optional[List[str]] = None

        # Parse all captions
        for caption in captions:
            # Safety measure to protect against empty portions of captioning
            if len(caption.text) >= 0:
                # Check for new speaker turn
                new_speaker_search = re.search(self.new_turn_pattern, caption.text)
                if new_speaker_search:
                    # Add previous speaker captions to all speaker captions
                    # (and reset current speaker captions)
                    if current_speaker_captions is not None:
                        all_speaker_captions.append(current_speaker_captions)
                        current_speaker_captions = None

                    # Create new current speaker
                    if current_speaker_captions is None:
                        current_speaker_captions = [caption]

                # Otherwise append
                else:
                    current_speaker_captions.append(caption)

        # Add the last current speaker caption
        # Fence-post problems
        all_speaker_captions.append(current_speaker_captions)

        # Parse speaker captions into timestamped sentences and words
        timestamped_sentences: List[Sentence] = []
        transcript_sentence_index = 0
        for speaker_captions in all_speaker_captions:
            all_sentences_words = []
            current_sentence_words = None

            # Clean new speaker markings
            for caption in speaker_captions:
                new_speaker_search = re.search(self.new_turn_pattern, caption.text)
                if new_speaker_search:
                    caption_text = new_speaker_search.group(2)
                else:
                    caption_text = caption.text

                # Look for sentence end
                sentence_end_search = re.search(
                    self.end_of_sentence_pattern, caption_text
                )
                # Add previous sentence text to all sentences
                # (and reset current sentence)
                if current_sentence_words is not None:
                    all_sentences_words.append(current_sentence_words)
                    current_sentence_words = None

                # Create new current sentence
                if current_sentence_words is None:
                    current_sentence_words = [caption_text]

                # Otherwise append
                else:
                    current_sentence_words.append(caption_text)

        return all_speaker_captions
