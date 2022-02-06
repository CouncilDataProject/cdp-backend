#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
from typing import Dict, List, Union

import numpy as np
from pydub import AudioSegment
from tqdm import tqdm
from transformers import pipeline

from ..pipeline.transcript_model import Transcript

###############################################################################

DEFAULT_MODEL = "trained-speakerbox"
TMP_AUDIO_CHUNK_SAVE_PATH = "tmp-audio-prediction-chunk.wav"

###############################################################################


def annotate(
    transcript: Union[str, Path, Transcript],
    audio: Union[str, Path, AudioSegment],
    model: str = DEFAULT_MODEL,
    min_intra_sentence_chunk_duration: float = 0.5,
    max_intra_sentence_chunk_duration: float = 2.0,
    min_sentence_mean_confidence: float = 0.985,
) -> Transcript:
    """
    Annotate a transcript using a pre-trained speaker identification model.
    """
    # Load transcript
    if isinstance(transcript, (str, Path)):
        with open(transcript, "r") as open_f:
            transcript = Transcript.from_json(open_f.read())

    # Load audio
    if isinstance(audio, (str, Path)):
        audio = AudioSegment.from_file(audio)

    # Load model
    classifier = pipeline("audio-classification", model=model)
    n_speakers = len(classifier.model.config.id2label)

    # Convert to millis
    min_intra_sentence_chunk_duration_millis = min_intra_sentence_chunk_duration * 1000
    max_intra_sentence_chunk_duration_millis = max_intra_sentence_chunk_duration * 1000

    # Iter transcript, get sentence audio, chunk into sections
    # of two seconds or less, classify each, and take most common,
    # with thresholding confidence * segments
    for sentence in tqdm(transcript.sentences):
        # Keep track of each sentence chunk classification and score
        chunk_scores: Dict[str, List[float]] = {}

        # Get audio slice for sentence
        sentence_start_millis = sentence.start_time * 1000
        sentence_end_millis = sentence.end_time * 1000

        # Split into smaller chunks
        for chunk_start_millis in np.arange(
            sentence_start_millis,
            sentence_end_millis,
            max_intra_sentence_chunk_duration_millis,
        ):
            # Tentative chunk end
            chunk_end_millis = (
                chunk_start_millis + max_intra_sentence_chunk_duration_millis
            )

            # Determine chunk end time
            # If start + chunk duration is longer than sentence
            # Chunk needs to be cut at sentence end
            if sentence_end_millis < chunk_end_millis:
                chunk_end_millis = sentence_end_millis

            # Only allow if duration is greater than min intra sentence chunk duration
            duration = chunk_end_millis - chunk_start_millis
            if duration >= min_intra_sentence_chunk_duration_millis:
                # Get chunk
                chunk = audio[chunk_start_millis:chunk_end_millis]

                # Write to temp
                chunk.export(TMP_AUDIO_CHUNK_SAVE_PATH, format="wav")

                # Predict and store scores for sentence
                preds = classifier(TMP_AUDIO_CHUNK_SAVE_PATH, top_k=n_speakers)
                for pred in preds:
                    if pred["label"] not in chunk_scores:
                        chunk_scores[pred["label"]] = []
                    chunk_scores[pred["label"]].append(pred["score"])

        # Create mean score
        sentence_speaker = None
        if len(chunk_scores) > 0:
            mean_scores: Dict[str, float] = {}
            for speaker, scores in chunk_scores.items():
                mean_scores[speaker] = sum(scores) / len(scores)

            # Get highest score speaker
            highest_mean_speaker = max(mean_scores, key=mean_scores.get)
            highest_mean_score = mean_scores[highest_mean_speaker]

            # Threshold holdout
            if highest_mean_score >= min_sentence_mean_confidence:
                sentence_speaker = highest_mean_speaker

        # Store to transcript
        sentence.speaker_name = sentence_speaker

    # Remove last made chunk file
    Path(TMP_AUDIO_CHUNK_SAVE_PATH).unlink()

    return transcript
