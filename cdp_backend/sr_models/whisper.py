#!/usr/bin/env python

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import spacy
import whisper
from pydub import AudioSegment
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

        timestamped_words_with_meta = []
        for segment in result["segments"]:
            seg_text = segment["text"]
            seg_text_as_words = seg_text.split(" ")
            seg_duration = segment["end"] - segment["start"]
            avg_word_duration = seg_duration / len(seg_text_as_words)
            for i, word in enumerate(seg_text_as_words):
                if len(word.strip()) > 0:
                    timestamped_words_with_meta.append(
                        {
                            "text": word,
                            "start": segment["start"] + (i * avg_word_duration),
                            "end": segment["start"] + ((i + 1) * avg_word_duration),
                        }
                    )

        # For some reason, whisper sometimes returns segments with
        # start and end times that are impossible
        # i.e. start and end of 185 second when the total audio duration is 180 seconds
        # Fix all timestamps by rescaling to audio duration
        # This is a hack -- but all of the word level timestamps are a hack anyway...
        whisper_reported_duration = timestamped_words_with_meta[-1]["end"]
        audio = AudioSegment.from_file(file_uri)
        file_reported_duration = audio.duration_seconds

        # Scale to between 0 and 1
        # Then rescale to real duration
        for word_with_meta in timestamped_words_with_meta:
            # Scale to between 0 and 1
            word_with_meta["start"] = (
                word_with_meta["start"] / whisper_reported_duration
            )
            word_with_meta["end"] = word_with_meta["end"] / whisper_reported_duration

            # Rescale to real duration
            word_with_meta["start"] = word_with_meta["start"] * file_reported_duration
            word_with_meta["end"] = word_with_meta["end"] * file_reported_duration

        # Iteratively construct sentences
        sentences = []
        current_sentence_words_with_metas = []
        for word_with_meta in timestamped_words_with_meta:
            current_sentence_words_with_metas.append(word_with_meta)
            joined_words = " ".join(
                [
                    word_with_meta["text"]
                    for word_with_meta in current_sentence_words_with_metas
                ]
            )

            # Check for sentences
            doc = self.nlp(joined_words)
            doc_sents = list(doc.sents)

            # If there is more than one sentence
            # Get the second sentence start index within the overall joined_words
            # Then split the joined_words at that start index to just get the
            # joined words in the first sentence
            # Then split those words to see how many are in the first sentence
            # The use that length to pull the same amount of words from the
            # current_sentence_words_with_metas list.
            if len(doc_sents) > 1:
                second_sent = doc_sents[1]
                second_sent_start_index = joined_words.index(second_sent.text)
                first_sent_joined_words = joined_words[:second_sent_start_index]
                first_sent_words = [
                    first_sent_word
                    for first_sent_word in first_sent_joined_words.split(" ")
                    if len(first_sent_word.strip()) > 0
                ]
                first_sent_extract = current_sentence_words_with_metas[
                    : len(first_sent_words)
                ]
                if len(first_sent_extract) > 0:
                    sentences.append(first_sent_extract)
                    current_sentence_words_with_metas = (
                        current_sentence_words_with_metas[len(first_sent_words) :]
                    )

        # If there is anything remaining, add it to sentences
        if len(current_sentence_words_with_metas) > 0:
            sentences.append(current_sentence_words_with_metas)

        # Reformat data to our structure
        structured_sentences: list[transcript_model.Sentence] = []
        for sent_index, sentence_with_word_metas in enumerate(sentences):
            structured_sentences.append(
                transcript_model.Sentence(
                    index=sent_index,
                    confidence=self.confidence,
                    start_time=sentence_with_word_metas[0]["start"],
                    end_time=sentence_with_word_metas[-1]["end"],
                    text=" ".join(
                        [
                            word_with_meta["text"]
                            for word_with_meta in sentence_with_word_metas
                        ]
                    ).strip(),
                    words=[
                        transcript_model.Word(
                            index=word_index,
                            start_time=word_with_meta["start"],
                            end_time=word_with_meta["end"],
                            text=self._clean_word(word_with_meta["text"]),
                        )
                        for word_index, word_with_meta in enumerate(
                            sentence_with_word_metas
                        )
                    ],
                )
            )

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
            sentences=structured_sentences,
        )
