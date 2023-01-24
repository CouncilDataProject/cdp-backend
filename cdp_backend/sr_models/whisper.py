#!/usr/bin/env python

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import spacy
import whisper
from spacy.cli.download import download as download_spacy_model

from .. import __version__
from ..pipeline import transcript_model
from .sr_model import SRModel

###############################################################################

log = logging.getLogger(__name__)

###############################################################################

spacy.prefer_gpu()

###############################################################################


MODEL_NAME_FAKE_CONFIDENCE_LUT = {
    "tiny": 0.5,
    "base": 0.6,
    "small": 0.65,
    "medium": 0.71,
    "large": 0.72,
}


class WhisperModel(SRModel):
    def __init__(
        self,
        model_name: str = "medium",
        confidence: float | None = None,
        **kwargs: Any,
    ):
        """
        Initialize an OpenAI Whisper Model Transcription processor.

        Parameters
        ----------
        model_name: str
            The model version to use. Default: "medium"
            See:
            https://github.com/openai/whisper/tree/0b5dcfdef7ec04250b76e13f1630e32b0935ce76#available-models-and-languages
        confidence: Optional[float]
            A confidence value to set for all transcripts produced by this SR Model.
            See source code for issues related to this.
            Default: None (lookup a fake confidence to use depending on model selected)
        kwargs: Any
            Any extra arguments to catch.
        """
        self.model_name = model_name

        # TODO: whisper doesn't provide a confidence value
        # Additionally, we have been overloading confidence with webvtt
        # conversion. We may want to get rid of confidence?
        # Our current confidence default is 0.001 higher than our old
        # WebVTT parser to ensure that these transcripts are chosen.
        if confidence is not None:
            self.confidence = confidence
        else:
            self.confidence = MODEL_NAME_FAKE_CONFIDENCE_LUT[model_name]

        # Init spacy
        try:
            self.nlp = spacy.load("en_core_web_trf")
        except Exception:
            download_spacy_model("en_core_web_trf")
            self.nlp = spacy.load("en_core_web_trf")

    def transcribe(
        self,
        file_uri: str | Path,
        **kwargs: Any,
    ) -> transcript_model.Transcript:
        """
        Transcribe audio from file and return a Transcript model.

        Parameters
        ----------
        file_uri: Union[str, Path]
            The uri to the audio file or caption file to transcribe.
        kwargs: Any
            Any extra arguments to catch.

        Returns
        -------
        outputs: transcript_model.Transcript
            The transcript model for the supplied media file.
        """
        log.info(f"Loading '{self.model_name}' whisper model to use for transcription.")
        model = whisper.load_model(self.model_name)

        log.info(f"Transcribing '{file_uri}'")
        result = model.transcribe(file_uri, verbose=False)

        # A safe string joiner
        # It ensures that strings are joined to each other with no
        # additional white spacing.
        def safe_str_join(str1: str, str2: str) -> str:
            return " ".join([str1.strip(), str2.strip()]).strip()

        # Split into sentences
        sentences: list[transcript_model.Sentence] = []
        current_sentence_index = 0
        current_sentence_start = -1.0
        current_sentence_text = ""
        for segment in result["segments"]:
            if current_sentence_start == -1.0:
                current_sentence_start = segment["start"]

            print("Current State:")
            print(f"\tlen(sentences): {len(sentences)}")
            print(f"\tsentences[-2:]: {[s.text for s in sentences[-2:]]}")
            print(f"\tcurrent_sentence_index: {current_sentence_index}")
            print(f"\tcurrent_sentence_text: '{current_sentence_text}'")

            # Pull out just the text and combine with prior state
            seg_text = segment["text"]
            seg_text_with_prior = safe_str_join(current_sentence_text, seg_text)

            # Segment duration and avg word duration
            seg_duration = segment["end"] - current_sentence_start
            seg_text_with_prior_as_words = seg_text_with_prior.split(" ")
            avg_word_duration = seg_duration / len(seg_text_with_prior_as_words)

            # Handle intra segment sentence
            doc = self.nlp(seg_text_with_prior)
            intra_segment_sentences = list(doc.sents)

            # Process all segment sentence chunks
            # Note, the last chunk may not be a complete sentence
            for intra_sent_index, intra_sent in enumerate(intra_segment_sentences):
                # If it isn't the last sentence, just process it.
                if intra_sent_index < len(intra_segment_sentences) - 1:
                    # Calculate this intra sentence start time offset
                    intra_sent_start_index = seg_text_with_prior.index(intra_sent.text)
                    percent_progress_in_sentence = intra_sent_start_index / len(
                        intra_sent.text
                    )
                    intra_sent_start_offset = (
                        current_sentence_start
                        + (percent_progress_in_sentence) * seg_duration
                    )

                    # Process words
                    intra_sent_raw_words = intra_sent.text.split(" ")
                    intra_sent_words: list[transcript_model.Word] = []
                    for word_index, word in enumerate(intra_sent_raw_words):
                        intra_sent_words.append(
                            transcript_model.Word(
                                index=word_index,
                                start_time=(
                                    intra_sent_start_offset
                                    + (word_index * avg_word_duration)
                                ),
                                end_time=(
                                    intra_sent_start_offset
                                    + ((word_index + 1) * avg_word_duration)
                                ),
                                text=self._clean_word(word),
                            )
                        )

                    # Add sentence to collection
                    sentences.append(
                        transcript_model.Sentence(
                            index=current_sentence_index,
                            confidence=self.confidence,
                            start_time=current_sentence_start,
                            end_time=intra_sent_words[-1].end_time,
                            words=intra_sent_words,
                            text=intra_sent.text,
                        )
                    )
                    # Update for next loop
                    current_sentence_index += 1

                # Store for next
                else:
                    current_sentence_text = intra_sent.text
                    current_sentence_start = -1.0

        # Return complete transcript object
        return transcript_model.Transcript(
            generator=(
                f"CDP Whisper Conversion "
                f"-- CDP v{__version__} "
                f"-- Whisper Model Name '{self.model_name}'"
            ),
            confidence=self.confidence,
            session_datetime=None,
            created_datetime=datetime.utcnow().isoformat(),
            sentences=sentences,
        )
