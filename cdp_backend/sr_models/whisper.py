#!/usr/bin/env python

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import spacy
from ctranslate2.converters import TransformersConverter
from faster_whisper import WhisperModel as FasterWhisper
from pydub import AudioSegment
from spacy.cli.download import download as download_spacy_model
from tqdm import tqdm

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
    "large-v2": 0.72,
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
        # Handle large -> large v2
        if model_name == "large":
            model_name = "large-v2"
        self.model_name = model_name

        # Convert whisper to faster whisper
        transformer_converter = TransformersConverter(
            f"openai/whisper-{self.model_name}"
        )
        self.converted_faster_whisper_model_path = transformer_converter.convert(
            output_dir=str(
                Path(f"./faster-whisper-models/{model_name}/").expanduser().resolve()
            ),
            quantization="float16",
            force=True,
        )

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
            self.nlp = spacy.load(
                "en_core_web_trf",
                # Only keep the parser
                # We are only using this for sentence parsing
                disable=[
                    "tagger",
                    "ner",
                    "lemmatizer",
                    "textcat",
                ],
            )
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
        model = FasterWhisper(self.converted_faster_whisper_model_path)

        log.info(f"Transcribing '{file_uri}'")
        segments, _ = model.transcribe(file_uri)

        log.info("Converting whisper segments to words with metadata")
        timestamped_words_with_meta = []
        for segment in tqdm(segments, desc="Transcribing segment..."):
            seg_text = segment.text
            seg_text_as_words = seg_text.split(" ")
            seg_duration = segment.end - segment.start
            avg_word_duration = seg_duration / len(seg_text_as_words)
            for i, word in enumerate(seg_text_as_words):
                if len(word.strip()) > 0:
                    timestamped_words_with_meta.append(
                        {
                            "text": word,
                            "start": segment.start + (i * avg_word_duration),
                            "end": segment.start + ((i + 1) * avg_word_duration),
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
        log.info("Calculating word durations")
        for word_with_meta in timestamped_words_with_meta:
            # Scale to between 0 and 1
            word_with_meta["start"] = (
                word_with_meta["start"] / whisper_reported_duration
            )
            word_with_meta["end"] = word_with_meta["end"] / whisper_reported_duration

            # Rescale to real duration
            word_with_meta["start"] = word_with_meta["start"] * file_reported_duration
            word_with_meta["end"] = word_with_meta["end"] * file_reported_duration

        # Process all text
        joined_all_words = " ".join(
            [word_with_meta["text"] for word_with_meta in timestamped_words_with_meta]
        )
        joined_all_words = re.sub(r" +", " ", joined_all_words)
        doc = self.nlp(joined_all_words)
        doc_sents = list(doc.sents)

        # Process sentences
        sentences_with_word_metas = []
        current_word_index_start = 0
        log.info("Constructing sentences with word metadata")
        for doc_sent in doc_sents:
            print(f"Doc sent: '{doc_sent}'")
            # Split the sentence
            doc_sent_words = doc_sent.text.split(" ")

            # Find the words
            word_subset = timestamped_words_with_meta[
                current_word_index_start : current_word_index_start
                + len(doc_sent_words)
            ]
            print(f"\tWords: {[w_w_m['text'] for w_w_m in word_subset]}")

            # Append the words
            sentences_with_word_metas.append(word_subset)

            # Increase the current word index start
            current_word_index_start = current_word_index_start + len(doc_sent_words)

        # Remove any length zero sentences
        sentences_with_word_metas = [
            sentence_with_word_metas
            for sentence_with_word_metas in sentences_with_word_metas
            if len(sentence_with_word_metas) > 0
        ]

        # Reformat data to our structure
        structured_sentences: list[transcript_model.Sentence] = []
        log.info("Converting sentences with word meta to transcript format")
        for sent_index, sentence_with_word_metas in enumerate(
            sentences_with_word_metas,
        ):
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