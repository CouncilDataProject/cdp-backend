#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, List, NamedTuple, Optional, Union

import fsspec
import nltk
import truecase
import webvtt
from webvtt.structures import Caption

from ..pipeline import transcript_model
from ..version import __version__
from .sr_model import SRModel

###############################################################################

log = logging.getLogger(__name__)

###############################################################################


class SpeakerRawBlock(NamedTuple):
    words: List[transcript_model.Word]
    raw_text: str


class WebVTTSRModel(SRModel):
    """
    Initialize a WebVTT Conversion Model.

    This doesn't do any actual speaker recognition, but rather will simply convert
    from WebVTT format into a CDP transcript object.

    Parameters
    ----------
    new_turn_pattern: str
        The character(s) to look for that indicate a new speaker turn.
        Default: "&gt;"
    confidence: float
        The confidence value to assign to the produced Transcript object.
        Default: 0.97
    """

    END_OF_SENTENCE_PATTERN = r"^.+[.?!]\s*$"

    def __init__(
        self,
        new_turn_pattern: str = "&gt;",
        confidence: float = 0.97,
        **kwargs: Any,
    ):
        # New speaker turn must begin with one or more new_turn_pattern str
        # This will create a regex pattern to allow for one or more of the pattern
        self.new_turn_pattern = r"({})+\s*(.+)".format(new_turn_pattern)

        # Confidence is tricky. We allow it to be a parameter because closed captions
        # aren't always 100% accurate. For Seattle, I would guess they are about 97%
        # accurate.
        self.confidence = confidence

    def _normalize_text(self, text: str) -> str:
        normalized_text = truecase.get_true_case(text)

        # Fix some punctuation issues, e.g. `roughly$ 19` becomes `roughly $19`
        normalized_text = re.sub(
            r"([#$(<[{]) ",
            lambda x: f" {x.group(1)}",
            normalized_text,
        )
        return normalized_text

    def _get_speaker_turns(self, captions: List[Caption]) -> List[List[Caption]]:
        # Create list of speaker turns
        speaker_turns: List[List[Caption]] = []
        # List of captions of a speaker turn
        speaker_turn_captions: List[Caption] = []
        for caption in captions:
            new_turn_search = re.search(self.new_turn_pattern, caption.text)

            # Caption block is start of a new speaker turn
            if new_turn_search:
                # Remove the new speaker turn pattern from caption's text
                caption.text = new_turn_search.group(2)
                # Append speaker turn to list of speaker turns
                if speaker_turn_captions:
                    speaker_turns.append(speaker_turn_captions)

                # Reset speaker_turn with this caption, for start of a new speaker turn
                speaker_turn_captions = [caption]

            # Caption block is not a start of a new speaker turn
            else:
                # Append caption to current speaker turn
                speaker_turn_captions.append(caption)

        # Add the last speaker turn
        if speaker_turn_captions:
            speaker_turns.append(speaker_turn_captions)

        return speaker_turns

    @staticmethod
    def _construct_sentence(
        lines: List[str],
        caption: Caption,
        start_time: float,
        confidence: float,
        speaker_index: int,
    ) -> transcript_model.Sentence:
        # Construct sentence and raw words for Word and sentence processing
        text = " ".join(lines)
        raw_words = text.split()

        # Calc caption duration
        # for linear interpolation of word offsets
        caption_duration = caption.end_in_seconds - caption.start_in_seconds

        # Create collection of words
        words: List[transcript_model.Word] = []
        for word_index, word in enumerate(raw_words):
            words.append(
                transcript_model.Word(
                    index=word_index,
                    start_time=(
                        # Linear words per second
                        # offset by start time of caption
                        caption.start_in_seconds
                        + ((word_index / len(raw_words)) * caption_duration)
                    ),
                    end_time=(
                        # Linear words per second
                        # offset by start time of caption + 1
                        caption.start_in_seconds
                        + (((word_index + 1) / len(raw_words)) * caption_duration)
                    ),
                    text=WebVTTSRModel._clean_word(word),
                )
            )

        # Append full sentence
        return transcript_model.Sentence(
            index=0,
            confidence=confidence,
            start_time=start_time,
            end_time=caption.end_in_seconds,
            text=text.capitalize(),
            words=words,
            speaker_name=None,
            speaker_index=speaker_index,
        )

    def _get_sentences(
        self,
        speaker_turn_captions: List[Caption],
        speaker_index: int,
    ) -> List[transcript_model.Sentence]:
        # Create timestamped sentences
        sentences = []
        # List of text, representing a sentence
        lines: List[str] = []
        start_time: Optional[float] = None
        for caption in speaker_turn_captions:
            if start_time is None:
                start_time = caption.start_in_seconds
            lines.append(caption.text)

            # Check for sentence end
            end_sentence_search = re.search(
                WebVTTSRModel.END_OF_SENTENCE_PATTERN,
                caption.text,
            )
            if end_sentence_search:
                sentences.append(
                    self._construct_sentence(
                        lines=lines,
                        caption=caption,
                        start_time=start_time,
                        confidence=self.confidence,
                        speaker_index=speaker_index,
                    )
                )

                # Reset lines and start_time, for start of new sentence
                lines = []
                start_time = None

        # If any leftovers in lines, add a sentence for that.
        if len(lines) > 0 and start_time is not None:
            sentences.append(
                self._construct_sentence(
                    lines=lines,
                    caption=speaker_turn_captions[-1],
                    start_time=start_time,
                    confidence=self.confidence,
                    speaker_index=speaker_index,
                )
            )

        return sentences

    def transcribe(
        self, file_uri: Union[str, Path], **kwargs: Any
    ) -> transcript_model.Transcript:
        """
        Converts a WebVTT closed caption file into the CDP Transcript Model.

        Parameters
        ----------
        file_uri: Union[str, Path]
            The file URI or path to the VTT file to convert.

        Returns
        -------
        transcript: transcript_model.Transcript
            The contents of the VTT file as a CDP Transcript.
        """
        # Download punkt for truecase module
        nltk.download("punkt")

        # Read the caption file
        with fsspec.open(file_uri, "rb") as open_resource:
            captions = webvtt.read(open_resource)

        # Get speaker turns
        speaker_turns = self._get_speaker_turns(captions=captions)

        # Parse turns for sentences
        sentences: List[transcript_model.Sentence] = []
        for speaker_index, speaker_turn in enumerate(speaker_turns):
            sentences += self._get_sentences(
                speaker_turn_captions=speaker_turn,
                speaker_index=speaker_index,
            )

        # Final processing and normalization
        for sentence_index, sentence in enumerate(sentences):
            sentence.index = sentence_index
            sentence.text = self._normalize_text(sentence.text)

        transcript = transcript_model.Transcript(
            generator=f"CDP WebVTT Conversion -- CDP v{__version__}",
            confidence=(sum([s.confidence for s in sentences]) / len(sentences)),
            session_datetime=None,
            created_datetime=datetime.utcnow().isoformat(),
            sentences=sentences,
        )
        log.info(f"Completed WebVTT transcript conversion for: {file_uri}")

        return transcript
