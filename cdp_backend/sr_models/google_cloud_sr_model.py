#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import logging
from pathlib import Path
from typing import Any, List, Optional, Union

from google.cloud import speech_v1p1beta1 as speech

from . import constants
from .sr_model import SRModel, SRModelOutputs

###############################################################################

log = logging.getLogger(__name__)

###############################################################################


class GoogleCloudSRModel(SRModel):
    def __init__(self, credentials_path: Union[str, Path], **kwargs: Any):
        # Resolve credentials
        self.credentials_path = Path(credentials_path).resolve(strict=True)

    @staticmethod
    def _clean_phrases(phrases: Optional[List[str]] = None) -> List[str]:
        if phrases:
            # Clean and apply usage limits
            cleaned = []
            total_character_count = 0
            for phrase in [p for p in phrases[:500] if isinstance(p, str)]:
                if total_character_count <= 9900:
                    cleaned_phrase = phrase[:100]

                    # Make the phrase a bit nicer by chunking to nearest complete word
                    if " " in cleaned_phrase:
                        cleaned_phrase = cleaned_phrase[: cleaned_phrase.rfind(" ")]

                    # Append cleaned phrase and increase character count
                    cleaned.append(cleaned_phrase)
                    total_character_count += len(cleaned_phrase)

            return cleaned
        else:
            return []

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
        timestamped_words_save_path = Path(timestamped_words_save_path).resolve()  # type: ignore
        timestamped_sentences_save_path = Path(
            timestamped_sentences_save_path  # type: ignore
        ).resolve()

        # Create client
        client = speech.SpeechClient.from_service_account_json(self.credentials_path)

        # Create basic metadata
        metadata = speech.types.RecognitionMetadata()
        metadata.interaction_type = (
            speech.enums.RecognitionMetadata.InteractionType.DISCUSSION
        )

        # Add phrases
        speech_context = speech.types.SpeechContext(
            phrases=self._clean_phrases(phrases)
        )

        # Prepare for transcription
        config = speech.types.RecognitionConfig(
            encoding=speech.enums.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
            enable_automatic_punctuation=True,
            enable_word_time_offsets=True,
            speech_contexts=[speech_context],
            metadata=metadata,
        )
        audio = speech.types.RecognitionAudio(uri=file_uri)

        # Begin transcription
        log.debug(f"Beginning transcription for: {file_uri}")
        operation = client.long_running_recognize(config, audio)

        # Wait for complete
        response = operation.result(timeout=10800)

        # Select highest confidence transcripts
        confidence_sum = 0
        segments = 0
        timestamped_words = []
        for result in response.results:
            # Some portions of audio may not have text
            if len(result.alternatives) > 0:
                # Check length of transcript result
                word_list = result.alternatives[0].words
                if len(word_list) > 0:
                    for word in word_list:
                        start_time = (
                            word.start_time.seconds + word.start_time.nanos * 1e-9
                        )
                        end_time = word.end_time.seconds + word.end_time.nanos * 1e-9
                        timestamped_words.append(
                            {
                                "text": word.word,
                                "start_time": start_time,
                                "end_time": end_time,
                            }
                        )

                    # Update confidence stats
                    confidence_sum += result.alternatives[0].confidence
                    segments += 1

        # Create timestamped sentences
        timestamped_sentences = []
        current_sentence = None
        for word_details in timestamped_words:
            # Create new sentence
            if current_sentence is None:
                current_sentence = {
                    "text": word_details["text"],
                    "start_time": word_details["start_time"],
                }
            # Update current sentence
            else:
                current_sentence["text"] += " {}".format(word_details["text"])

            # End current sentence and reset
            if word_details["text"][-1] == ".":
                current_sentence["end_time"] = word_details["end_time"]
                timestamped_sentences.append(current_sentence)
                current_sentence = None

        # Create raw transcript
        raw_transcript = " ".join(
            [sentence_details["text"] for sentence_details in timestamped_sentences]
        )
        raw_transcript_with_time = [
            {
                "start_time": 0,
                "text": raw_transcript,
                "end_time": timestamped_words[-1]["end_time"],
            }
        ]

        # Compute mean confidence
        if segments > 0:
            confidence = confidence_sum / segments
        else:
            confidence = 0.0
        log.info(f"Completed transcription for: {file_uri}. Confidence: {confidence}")

        # Wrap each transcript in the standard format
        raw_transcript_wrapped = self.wrap_and_format_transcript_data(
            data=raw_transcript_with_time,
            transcript_format=constants.TranscriptFormats.raw,
            confidence=confidence,
        )
        timestamped_words_wrapped = self.wrap_and_format_transcript_data(
            data=timestamped_words,
            transcript_format=constants.TranscriptFormats.timestamped_words,
            confidence=confidence,
        )
        timestamped_sentences_wrapped = self.wrap_and_format_transcript_data(
            data=timestamped_sentences,
            transcript_format=constants.TranscriptFormats.timestamped_sentences,
            confidence=confidence,
        )

        # Write files
        with open(timestamped_words_save_path, "w") as write_out:
            json.dump(timestamped_words_wrapped, write_out)

        with open(timestamped_sentences_save_path, "w") as write_out:
            json.dump(timestamped_sentences_wrapped, write_out)

        with open(raw_transcript_save_path, "w") as write_out:
            json.dump(raw_transcript_wrapped, write_out)

        # Return the save path
        return SRModelOutputs(
            raw_transcript_save_path,
            confidence,
            timestamped_words_save_path,
            timestamped_sentences_save_path,
        )
