#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import nltk
import requests
import truecase
import webvtt

from . import constants
from .sr_model import SRModel, SRModelOutputs

###############################################################################

log = logging.getLogger(__name__)

###############################################################################


class WebVTTSRModel(SRModel):
    def __init__(self, new_turn_pattern: str, confidence: float = 1, **kwargs):
        # Download punkt for truecase module
        nltk.download("punkt")
        # New speaker turn must begin with one or more new_turn_pattern str
        self.new_turn_pattern = r"({})+\s*(.+)$".format(new_turn_pattern)
        # Sentence must be ended by period, question mark, or exclamation point.
        self.end_of_sentence_pattern = r"^.+[.?!]\s*$"

        # Confidence is tricky. We allow it to be a parameter because closed captions
        # aren't always 100% accurate. For Seattle, I would guess they are about 97%
        # accurate.
        # Maybe something todo in the future is actually compute their accuracy.
        self.confidence = confidence

    def _normalize_text(self, text: str) -> str:
        normalized_text = truecase.get_true_case(text)
        # Fix some punctuation issue, e.g. `roughly$ 19` bececomes `roughly $19`
        normalized_text = re.sub(
            r"([#$(<[{]) ", lambda x: f" {x.group(1)}", normalized_text
        )
        return normalized_text

    def _request_caption_content(self, file_uri: str) -> str:
        # Get the content of file_uri
        response = requests.get(file_uri)
        response.raise_for_status()
        return response.text

    def _get_captions(
        self, closed_caption_content: str
    ) -> List[webvtt.structures.Caption]:
        # Create file-like object of caption file's content
        buffer = io.StringIO(closed_caption_content)
        # Get list of caption blocks
        captions = webvtt.read_buffer(buffer).captions
        buffer.close()
        return captions

    def _get_speaker_turns(
        self, captions: List[webvtt.structures.Caption]
    ) -> List[List[webvtt.structures.Caption]]:
        # Create list of speaker turns
        speaker_turns = []
        # List of captions of a speaker turn
        speaker_turn = []
        for caption in captions:
            new_turn_search = re.search(self.new_turn_pattern, caption.text)
            # Caption block is start of a new speaker turn
            if new_turn_search:
                # Remove the new speaker turn pattern from caption's text
                caption.text = new_turn_search.group(2)
                # Append speaker turn to list of speaker turns
                if speaker_turn:
                    speaker_turns.append(speaker_turn)
                # Reset speaker_turn with this caption, for start of a new speaker turn
                speaker_turn = [caption]
            # Caption block is not a start of a new speaker turn
            else:
                # Append caption to current speaker turn
                speaker_turn.append(caption)
        # Add the last speaker turn
        if speaker_turn:
            speaker_turns.append(speaker_turn)
        return speaker_turns

    def _get_sentences(
        self, speaker_turn: List[webvtt.structures.Caption]
    ) -> List[Dict[str, Union[str, float]]]:
        # Create timestamped sentences
        sentences = []
        # List of text, representing a sentence
        lines = []
        start_time = 0
        for caption in speaker_turn:
            start_time = start_time or caption.start_in_seconds
            lines.append(caption.text)
            end_sentence_search = re.search(self.end_of_sentence_pattern, caption.text)
            # Caption block is a end of sentence block
            if end_sentence_search:
                sentence = {
                    "start_time": start_time,
                    "end_time": caption.end_in_seconds,
                    "text": " ".join(lines),
                }
                sentences.append(sentence)
                # Reset lines and start_time, for start of new sentence
                lines = []
                start_time = 0

        # If any leftovers in lines, add a sentence for that.
        if lines:
            sentences.append(
                {
                    "start_time": start_time,
                    "end_time": speaker_turn[-1].end_in_seconds,
                    "text": " ".join(lines),
                }
            )
        return sentences

    def _create_timestamped_speaker_turns(
        self, speaker_turns: List[List[webvtt.structures.Caption]]
    ) -> List[Dict[str, Union[str, List[Dict[str, Union[str, float]]]]]]:
        timestamped_speaker_turns = []
        for speaker_turn in speaker_turns:
            # Get timestamped sentences for a speaker turn
            sentences = self._get_sentences(speaker_turn)
            timestamped_speaker_turns.append({"speaker": "", "data": sentences})
        return timestamped_speaker_turns

    def transcribe(
        self,
        file_uri: Union[str, Path],
        raw_transcript_save_path: Union[str, Path],
        timestamped_words_save_path: Optional[Union[str, Path]] = None,
        timestamped_sentences_save_path: Optional[Union[str, Path]] = None,
        timestamped_speaker_turns_save_path: Optional[Union[str, Path]] = None,
        phrases: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> SRModelOutputs:
        # Check paths
        raw_transcript_save_path = Path(raw_transcript_save_path).resolve()
        timestamped_sentences_save_path = Path(
            timestamped_sentences_save_path
        ).resolve()
        timestamped_speaker_turns_save_path = Path(
            timestamped_speaker_turns_save_path
        ).resolve()

        # Get content of file uri
        closed_caption_content = self._request_caption_content(file_uri)
        # Get list of caption blocks from closed caption file
        captions = self._get_captions(closed_caption_content)
        # Convert list of caption blocks to list of speaker turns
        speaker_turns = self._get_speaker_turns(captions)
        # Create timestamped speaker turns transcript
        timestamped_speaker_turns = self._create_timestamped_speaker_turns(
            speaker_turns
        )
        # Normalized the text of transcript
        for speaker_turn in timestamped_speaker_turns:
            for sentence in speaker_turn["data"]:
                normalized_sentence_text = self._normalize_text(sentence["text"])
                sentence["text"] = normalized_sentence_text

        # Create raw transcript
        raw_text = " ".join(
            [
                sentence["text"]
                for turn in timestamped_speaker_turns
                for sentence in turn["data"]
            ]
        )
        raw_transcript = [
            {
                "start_time": timestamped_speaker_turns[0]["data"][0]["start_time"],
                "end_time": timestamped_speaker_turns[-1]["data"][-1]["end_time"],
                "text": raw_text,
            }
        ]

        # Create timestamped sentences transcript
        timestamped_sentences = [
            sentence for turn in timestamped_speaker_turns for sentence in turn["data"]
        ]

        # Log completed
        log.info(
            f"Completed transcription for: {file_uri}. Confidence: {self.confidence}"
        )
        # Wrap each transcript in the standard format
        raw_transcript = self.wrap_and_format_transcript_data(
            data=raw_transcript,
            transcript_format=constants.TranscriptFormats.raw,
            confidence=self.confidence,
        )

        timestamped_sentences = self.wrap_and_format_transcript_data(
            data=timestamped_sentences,
            transcript_format=constants.TranscriptFormats.timestamped_sentences,
            confidence=self.confidence,
        )

        timestamped_speaker_turns = self.wrap_and_format_transcript_data(
            data=timestamped_speaker_turns,
            transcript_format=constants.TranscriptFormats.timestamped_speaker_turns,
            confidence=self.confidence,
        )

        # Write files
        with open(raw_transcript_save_path, "w") as write_out:
            json.dump(raw_transcript, write_out)

        with open(timestamped_sentences_save_path, "w") as write_out:
            json.dump(timestamped_sentences, write_out)

        with open(timestamped_speaker_turns_save_path, "w") as write_out:
            json.dump(timestamped_speaker_turns, write_out)

        # Return the save path
        return SRModelOutputs(
            raw_path=raw_transcript_save_path,
            confidence=self.confidence,
            timestamped_sentences_path=timestamped_sentences_save_path,
            timestamped_speaker_turns_path=timestamped_speaker_turns_save_path,
        )
