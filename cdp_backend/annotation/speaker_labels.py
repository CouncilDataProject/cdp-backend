#!/usr/bin/env python

from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

import numpy as np
from pydub import AudioSegment
from tqdm import tqdm
from transformers import pipeline
from transformers.pipelines.base import Pipeline

from ..pipeline.transcript_model import Transcript

###############################################################################

log = logging.getLogger(__name__)

###############################################################################

DEFAULT_MODEL = "trained-speakerbox"

###############################################################################


def annotate(  # noqa: C901
    transcript: str | Path | Transcript,
    audio: str | Path | AudioSegment,
    model: str | Pipeline = DEFAULT_MODEL,
    min_intra_sentence_chunk_duration: float = 0.5,
    max_intra_sentence_chunk_duration: float = 2.0,
    min_sentence_mean_confidence: float = 0.985,
) -> Transcript:
    """
    Annotate a transcript using a pre-trained speaker identification model.

    Parameters
    ----------
    transcript: Union[str, Path, Transcript]
        The path to or an already in-memory Transcript object to fill with speaker
        name annotations.
    audio: Union[str, Path, AudioSegment]
        The path to the matching audio for the associated transcript.
    model: Union[str, Pipeline]
        The path to the trained Speakerbox audio classification model or a preloaded
        audio classification Pipeline.
        Default: "trained-speakerbox"
    min_intra_sentence_chunk_duration: float
        The minimum duration of a sentence to annotate. Anything less than this
        will be ignored from annotation.
        Default: 0.5 seconds
    max_intra_sentence_chunk_duration: float
        The maximum duration for a sentences audio to split to. This should match
        whatever was used during model training
        (i.e. trained on 2 second audio chunks, apply on 2 second audio chunks)
        Default: 2 seconds
    min_sentence_mean_confidence: float
        The minimum allowable mean confidence of all predicted chunk confidences
        to determine if the predicted label should be commited as an annotation
        or not.
        Default: 0.985

    Returns
    -------
    Transcript
        The annotated transcript. Note this updates in place, this does not return a new
        Transcript object.

    Notes
    -----
    A plain text walkthrough of this function is as follows:

    For each sentence in the provided transcript, the matching audio portion is
    retrieved, for example if the sentence start time is 12.05 seconds and end time is
    20.47 seconds, that exact portion of audio is pulled from the full audio file.

    If the audio duration for the chunk is less than the
    `min_intra_sentence_chunk_duration`, we ignore the sentence.

    If the audio duration for the chunk is greater than
    `max_intra_sentence_chunk_duration`, the audio is split into chunks of length
    `max_intra_sentence_chunk_duration` (i.e. from 12.05 to 14.05, from 14.05 to 16.05,
    etc. if the last chunk is less than the `min_intra_sentence_chunk_duration`, it is
    ignored).

    Each audio chunk is ran through the audio classification model and predicts every
    known person to the model. Each prediction has a confidence attached to it.
    The confidence values are used to create a dictionary of:
    `label -> list of confidence values`. Once all chunks for a single sentence is
    predicted, the mean confidence is computed for each.

    The label with the highest mean confidence is used as the sentence speaker name.
    If the highest mean confidence is less than the `min_sentence_mean_confidence`,
    no label is stored in the `speaker_name` sentence property (thresholded out).
    """
    # Generate random uuid filename for storing temp audio chunks
    tmp_audio_chunk_save_path = f"tmp-audio-chunk--{str(uuid4())}.wav"

    # Load transcript
    if isinstance(transcript, (str, Path)):
        with open(transcript) as open_f:
            loaded_transcript = Transcript.from_json(open_f.read())
    else:
        loaded_transcript = transcript

    # Load audio
    if isinstance(audio, (str, Path)):
        audio = AudioSegment.from_file(audio)

    # Load model
    if isinstance(model, str):
        classifier = pipeline("audio-classification", model=model)
    else:
        classifier = model
    n_speakers = len(classifier.model.config.id2label)

    # Convert to millis
    min_intra_sentence_chunk_duration_millis = min_intra_sentence_chunk_duration * 1000
    max_intra_sentence_chunk_duration_millis = max_intra_sentence_chunk_duration * 1000

    # Iter transcript, get sentence audio, chunk into sections
    # of two seconds or less, classify each, and take most common,
    # with thresholding confidence * segments
    met_threshold = 0
    missed_threshold = 0
    log.info("Annotating sentences with speaker names")
    for i, sentence in tqdm(
        enumerate(loaded_transcript.sentences),
        desc="Sentences annotated",
    ):
        # Keep track of each sentence chunk classification and score
        chunk_scores: dict[str, list[float]] = {}

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
                chunk.export(tmp_audio_chunk_save_path, format="wav")

                # Predict and store scores for sentence
                preds = classifier(tmp_audio_chunk_save_path, top_k=n_speakers)
                for pred in preds:
                    if pred["label"] not in chunk_scores:
                        chunk_scores[pred["label"]] = []
                    chunk_scores[pred["label"]].append(pred["score"])

        # Create mean score
        sentence_speaker = None
        if len(chunk_scores) > 0:
            mean_scores: dict[str, float] = {}
            for speaker, scores in chunk_scores.items():
                mean_scores[speaker] = sum(scores) / len(scores)

            # Get highest scoring speaker and their score
            highest_mean_speaker = ""
            highest_mean_score = 0.0
            for speaker, score in mean_scores.items():
                if score > highest_mean_score:
                    highest_mean_speaker = speaker
                    highest_mean_score = score

            # Threshold holdout
            if highest_mean_score >= min_sentence_mean_confidence:
                sentence_speaker = highest_mean_speaker
                met_threshold += 1
            else:
                log.debug(
                    f"Missed speaker annotation confidence threshold for sentence {i} "
                    f"-- Highest Mean Confidence: {highest_mean_score}"
                )
                missed_threshold += 1

        # Store to transcript
        sentence.speaker_name = sentence_speaker

    # Remove last made chunk file
    Path(tmp_audio_chunk_save_path).unlink()
    log.info(
        f"Total sentences: {len(loaded_transcript.sentences)}, "
        f"Sentences Annotated: {met_threshold}, "
        f"Missed Threshold: {missed_threshold}"
    )

    return loaded_transcript
