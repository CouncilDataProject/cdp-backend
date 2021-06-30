#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, List, NamedTuple, Union

import fsspec
import nltk
import truecase
import webvtt
from spacy.lang.en import English
from webvtt.structures import Caption

from ..pipeline.transcript_model import Sentence, Transcript, Word
from .sr_model import SRModel

###############################################################################

log = logging.getLogger(__name__)

###############################################################################


class SpeakerRawBlock(NamedTuple):
    words: List[Word]
    raw_text: str


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
        """
        Converts a WebVTT closed caption file into the CDP Transcript Model.

        Parameters
        ----------
        file_uri: Union[str, Path]
            The file URI or path to the VTT file to convert.

        Returns
        -------
        transcript: Transcript
            The contents of the VTT file as a CDP Transcript.
        """
        # Download punkt for truecase module
        nltk.download("punkt")

        # Read the caption file
        with fsspec.open(file_uri, "rb") as open_resource:
            captions = webvtt.read(open_resource)

        # Keep track of current speaker caption collection
        all_speaker_captions: List[List[Caption]] = []
        current_speaker_captions: List[Caption] = []

        # Parse all captions
        for caption in captions:
            # Safety measure to protect against empty portions of captioning
            if len(caption.text) >= 0:
                # Check for new speaker turn
                new_speaker_search = re.search(self.new_turn_pattern, caption.text)
                if new_speaker_search:
                    # Add previous speaker captions to all speaker captions
                    # (and reset current speaker captions)
                    if len(current_speaker_captions) > 0:
                        all_speaker_captions.append(current_speaker_captions)
                        current_speaker_captions = []

                # Start new speaker
                if len(current_speaker_captions) == 0:
                    current_speaker_captions = [caption]

                # Create new current speaker
                else:
                    current_speaker_captions.append(caption)

        # Add the last current speaker caption
        # Fence-post problem
        if len(current_speaker_captions) > 0:
            all_speaker_captions.append(current_speaker_captions)

        # Parse speaker captions one giant sentence of words, we will run sentencizer
        # afterwards as it's safer / more robust than our regex.
        all_speaker_sentences: List[SpeakerRawBlock] = []
        for speaker_captions in all_speaker_captions:
            current_speaker_words = []

            # Clean new speaker markings
            for caption in speaker_captions:
                new_speaker_search = re.search(self.new_turn_pattern, caption.text)
                if new_speaker_search:
                    caption_text = new_speaker_search.group(2)
                else:
                    caption_text = caption.text

                # Calc caption duration
                # for linear interpolation of word offsets
                caption_duration = caption.end_in_seconds - caption.start_in_seconds

                # Add words
                raw_words = caption_text.split()
                for i, word in enumerate(raw_words):
                    current_speaker_words.append(
                        Word(
                            index=0,
                            start_time=(
                                # Linear words per second
                                # offset by start time of caption
                                caption.start_in_seconds
                                + ((i / len(raw_words)) * caption_duration)
                            ),
                            end_time=(
                                # Linear words per second
                                # offset by start time of caption + 1
                                caption.start_in_seconds
                                + (((i + 1) / len(raw_words)) * caption_duration)
                            ),
                            text=self._clean_word(word),
                            # Temp raw word storage
                            # will remove after we truecase and sentenceizer
                            annotations={"raw": word},
                        )
                    )

            # Store the whole raw speaker block as a single list of words and the joined
            # raw text. We will use the spacy sentencizer and truecasing after this to
            # produce better overall results.
            all_speaker_sentences.append(
                SpeakerRawBlock(
                    words=current_speaker_words,
                    raw_text=" ".join(
                        [
                            word.annotations["raw"]
                            for word in current_speaker_words
                            if word.annotations is not None
                        ],
                    ),
                )
            )

        # Split single sentence into many for each speaker and truecase the whole block
        nlp = English()
        nlp.add_pipe("sentencizer")

        timestamped_sentences: List[Sentence] = []
        current_timestamped_sentence_index = 0
        for speaker_index, all_speaker_sentence in enumerate(all_speaker_sentences):
            # Truecase and sentence
            truecased = self._normalize_text(all_speaker_sentence.raw_text)
            sentences = [str(s).capitalize() for s in nlp(truecased).sents]

            # Make actual transcript
            overall_word_index = 0
            for sentence_index, sentence in enumerate(sentences):
                sentence_words = []
                for word_index, word in enumerate(sentence.split()):
                    existing_word = all_speaker_sentence.words[overall_word_index]
                    sentence_words.append(
                        Word(
                            index=word_index,
                            start_time=existing_word.start_time,
                            end_time=existing_word.end_time,
                            text=existing_word.text,
                            annotations=None,
                        )
                    )
                    overall_word_index += 1

                # Append the full sentence details
                timestamped_sentences.append(
                    Sentence(
                        index=current_timestamped_sentence_index,
                        confidence=self.confidence,
                        start_time=min([word.start_time for word in sentence_words]),
                        end_time=max([word.end_time for word in sentence_words]),
                        words=sentence_words,
                        text=sentence,
                        speaker_index=speaker_index,
                        speaker_name=None,
                        annotations=None,
                    )
                )
                current_timestamped_sentence_index += 1

        return Transcript(
            confidence=(
                sum([s.confidence for s in timestamped_sentences])
                / len(timestamped_sentences)
            ),
            generator="CDP WebVTT Conversion",
            session_datetime=None,
            created_datetime=datetime.utcnow(),
            sentences=timestamped_sentences,
            annotations=None,
        )
