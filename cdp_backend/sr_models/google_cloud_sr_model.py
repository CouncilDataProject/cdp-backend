#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Union

from google.cloud import speech_v1p1beta1 as speech

from ..pipeline.transcript_model import Sentence, Transcript, Word
from .sr_model import SRModel

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
        phrases: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Transcript:
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
        # timestamped_words = []

        # Create timestamped sentences
        timestamped_sentences: List[Sentence] = []
        current_sentence = None
        sentence_index = 0
        word_index = 0

        for result in response.results:
            # Some portions of audio may not have text
            if len(result.alternatives) > 0:
                # Check length of transcript result
                word_list = result.alternatives[0].words
                # print(str(word_list))
                if len(word_list) > 0:
                    for word in word_list:
                        # create Word
                        start_time = (
                            word.start_time.seconds + word.start_time.nanos * 1e-9
                        )
                        end_time = word.end_time.seconds + word.end_time.nanos * 1e-9

                        # Clean everything but non-delimiting characters
                        regex = re.compile(r"[^a-zA-Z0-9'\-]")
                        cleaned_word = regex.sub("", word.word)
                        timestamped_word = Word(
                            index=word_index,
                            start_time=start_time,
                            end_time=end_time,
                            text=cleaned_word,
                            # TODO: Add annotations
                            annotations=None,
                        )

                        if current_sentence is None:
                            current_sentence = Sentence(
                                index=sentence_index,
                                confidence=result.alternatives[0].confidence,
                                start_time=word.start_time,
                                end_time=word.end_time,
                                # TODO: Add speaker and annotations
                                speaker=None,
                                annotations=None,
                                words=[timestamped_word],
                                text=word.word,
                            )
                            word_index += 1

                        # End current sentence and reset
                        # TODO: Account for non-sentence ending periods, such as
                        # prefixes like "Mr." or "Dr."
                        elif bool(re.match(r"\.|\?", word.word[-1])):
                            # Finish sentence and append
                            current_sentence.end_time = word.end_time
                            current_sentence.text += " {}".format(word.word)
                            current_sentence.words.append(timestamped_word)

                            timestamped_sentences.append(current_sentence)

                            # Adjust indices
                            current_sentence = None
                            sentence_index += 1
                            word_index = 0

                        # Update current sentence
                        else:
                            current_sentence.text += " {}".format(word.word)
                            current_sentence.words.append(timestamped_word)
                            word_index += 1

                    # Update confidence stats
                    confidence_sum += result.alternatives[0].confidence
                    segments += 1

        # Compute mean confidence
        if segments > 0:
            confidence = confidence_sum / segments
        else:
            confidence = 0.0
        log.info(f"Completed transcription for: {file_uri}. Confidence: {confidence}")

        # Create transcript model
        transcript = Transcript(
            confidence=confidence,
            generator="Google Speech-to-Text",
            session_datetime=None,
            created_datetime=datetime.utcnow().isoformat(),
            sentences=timestamped_sentences,
            annotations=None,
        )

        return transcript
