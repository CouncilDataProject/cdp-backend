#!/usr/bin/env python

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Union

import whisper

from .. import __version__
from ..pipeline import transcript_model
from .sr_model import SRModel

###############################################################################

log = logging.getLogger(__name__)

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
        confidence: Optional[float] = None,
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

    def transcribe(
        self,
        file_uri: Union[str, Path],
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
        sentences: List[transcript_model.Sentence] = []
        current_sentence_index = 0
        current_sentence_start = -1.0
        current_sentence_text = ""
        for segment in result["segments"]:
            # Update current state
            if current_sentence_start == -1.0:
                current_sentence_start = segment["start"]

            seg_text = segment["text"]

            # Check if ending punctuation is present
            if any(seg_text.endswith(punct) for punct in [".", "?", "!"]):
                # Save str join
                current_sentence_text = safe_str_join(current_sentence_text, seg_text)

                # Calc caption duration for linear interpolation of word time offsets
                sentence_duration = segment["end"] - current_sentence_start

                # Create collection of words
                words: List[transcript_model.Word] = []
                raw_words = current_sentence_text.split(" ")
                for word_index, word in enumerate(raw_words):
                    words.append(
                        transcript_model.Word(
                            index=word_index,
                            start_time=(
                                # Linear words per second
                                # offset by start time of caption
                                current_sentence_start
                                + ((word_index / len(raw_words)) * sentence_duration)
                            ),
                            end_time=(
                                # Linear words per second
                                # offset by start time of caption + 1
                                current_sentence_start
                                + (
                                    ((word_index + 1) / len(raw_words))
                                    * sentence_duration
                                )
                            ),
                            text=WhisperModel._clean_word(word),
                        )
                    )

                sentences.append(
                    transcript_model.Sentence(
                        index=current_sentence_index,
                        confidence=self.confidence,
                        start_time=current_sentence_start,
                        end_time=segment["end"],
                        words=words,
                        text=current_sentence_text,
                    )
                )

                # Update for next loop
                current_sentence_index += 1
                current_sentence_start = -1.0
                current_sentence_text = ""
            else:
                current_sentence_text = safe_str_join(current_sentence_text, seg_text)

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
