#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Union

from google.cloud import speech_v1p1beta1 as speech
from spacy.lang.en import English

from ..pipeline import transcript_model
from ..version import __version__
from .sr_model import SRModel

###############################################################################

log = logging.getLogger(__name__)

###############################################################################

GOOGLE_SPEECH_ADAPTION_CLASSES = speech.SpeechContext(
    phrases=[
        # Location
        "$OOV_CLASS_ORDINAL",
        "$ADDRESSNUM",
        "$POSTALCODE",
        "$STREET",
        # Numbers
        "$MONEY",
        "$OPERAND",
        "$PERCENT",
        # Time
        "$TIME",
        "$DAY",
        "$MONTH",
        "$YEAR",
    ],
)

###############################################################################


class GoogleCloudSRModel(SRModel):
    def __init__(self, credentials_file: Union[str, Path], **kwargs: Any):
        # Resolve credentials
        self.credentials_file = Path(credentials_file).resolve(strict=True)

    @staticmethod
    def _clean_phrases(phrases: Optional[List[str]] = None) -> List[str]:
        """
        Notes
        -----
        This function will always leave room for the standard class tokens
        we use to optimize / adapt the Google Speech-to-Text model by limiting
        the total number of phrases added to the context object to
        500 minus the number of specific classes we use.

        See more information on adaption and class tokens here:
        https://cloud.google.com/speech-to-text/docs/speech-adaptation
        """
        if phrases:
            # Clean and apply usage limits
            cleaned = []
            total_character_count = 0
            for phrase in [
                p
                for p in phrases[: 500 - len(GOOGLE_SPEECH_ADAPTION_CLASSES.phrases)]
                if isinstance(p, str)
            ]:
                if total_character_count <= 9900:
                    cleaned_phrase = phrase[:100]

                    # Make the phrase a bit nicer by chunking to nearest complete word
                    if " " in cleaned_phrase:
                        cleaned_phrase = cleaned_phrase[: cleaned_phrase.rfind(" ")]

                    # Append cleaned phrase and increase character count
                    cleaned.append(cleaned_phrase)
                    total_character_count += len(cleaned_phrase)

            return cleaned
        return []

    def transcribe(
        self,
        file_uri: Union[str, Path],
        phrases: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> transcript_model.Transcript:
        """
        Transcribe audio from GCS file and return a Transcript model.

        Parameters
        ----------
        file_uri: Union[str, Path]
            The GCS file uri to the audio file or caption file to transcribe.
            It should be in format 'gs://...'.
        phrases: Optional[List[str]] = None
            A list of strings to feed as targets to the model.

        Returns
        -------
        outputs: transcript_model.Transcript
            The transcript model for the supplied media file.
        """
        # Create client
        client = speech.SpeechClient.from_service_account_file(
            filename=str(self.credentials_file)
        )

        # Create basic metadata
        metadata = speech.RecognitionMetadata()
        metadata.interaction_type = (
            speech.RecognitionMetadata.InteractionType.PHONE_CALL
        )
        metadata.original_media_type = (
            speech.RecognitionMetadata.OriginalMediaType.VIDEO
        )

        # Add phrases
        event_metadata_speech_context = speech.SpeechContext(
            phrases=self._clean_phrases(phrases)
        )

        # Prepare for transcription
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
            enable_automatic_punctuation=True,
            enable_word_time_offsets=True,
            enable_spoken_punctuation=True,
            speech_contexts=[
                GOOGLE_SPEECH_ADAPTION_CLASSES,
                event_metadata_speech_context,
            ],
            metadata=metadata,
            model="video",
            use_enhanced=True,
        )
        audio = speech.RecognitionAudio(uri=file_uri)

        # Begin transcription
        log.debug(f"Beginning transcription for: {file_uri}")
        operation = client.long_running_recognize(
            request={"config": config, "audio": audio}
        )

        # Wait for complete
        response = operation.result(timeout=10800)

        # Select highest confidence transcripts
        confidence_sum = 0
        segments = 0

        # Create timestamped sentences
        timestamped_sentences: List[transcript_model.Sentence] = []
        transcript_sentence_index = 0

        # Create sentence boundary pipeline
        nlp = English()
        nlp.add_pipe("sentencizer")

        for result in response.results:
            # Some portions of audio may not have text
            if len(result.alternatives) > 0:
                # Split transcript into sentences
                doc = nlp(result.alternatives[0].transcript)

                # Convert generator to list
                sentences = [str(sent) for sent in doc.sents]

                # Index holder for word results of response
                w_marker = 0
                for s_ind, _ in enumerate(sentences):
                    # Sentence text
                    s_text = sentences[s_ind]

                    num_words = len(s_text.split())

                    # Initialize sentence model
                    timestamped_sentence = transcript_model.Sentence(
                        index=transcript_sentence_index,
                        confidence=result.alternatives[0].confidence,
                        # Start and end time are placeholder values
                        start_time=0.0,
                        end_time=0.0,
                        words=[],
                        text=s_text,
                    )

                    for w_ind in range(w_marker, w_marker + num_words):
                        # Extract word from response
                        word = result.alternatives[0].words[w_ind]

                        # Nanos no longer supported, use microseconds instead
                        # https://github.com/googleapis/python-speech/issues/71
                        start_time = (
                            word.start_time.seconds
                            + word.start_time.microseconds * 1e-6
                        )

                        end_time = (
                            word.end_time.seconds + word.end_time.microseconds * 1e-6
                        )

                        # Add start_time to Sentence if first word
                        if w_ind - w_marker == 0:
                            timestamped_sentence.start_time = start_time

                        # Add end_time to Sentence if last word
                        if (w_ind - w_marker) == (num_words - 1):
                            timestamped_sentence.end_time = end_time

                        # Create Word model
                        timestamped_word = transcript_model.Word(
                            index=w_ind - w_marker,
                            start_time=start_time,
                            end_time=end_time,
                            text=self._clean_word(word.word),
                        )

                        timestamped_sentence.words.append(timestamped_word)

                    # Increment word marker
                    w_marker += num_words

                    # Add Sentence to sentence list
                    timestamped_sentences.append(timestamped_sentence)

                    # Increment transcript sentence index
                    transcript_sentence_index += 1

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
        transcript = transcript_model.Transcript(
            generator=f"Google Speech-to-Text -- CDP v{__version__}",
            confidence=confidence,
            session_datetime=None,
            created_datetime=datetime.utcnow().isoformat(),
            sentences=timestamped_sentences,
        )

        return transcript
