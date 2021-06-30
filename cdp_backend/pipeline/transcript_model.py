#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from dataclasses_json import dataclass_json

###############################################################################


@dataclass_json
@dataclass
class Word:
    """
    Data for a word in a transcript.

    Parameters
    ----------
    index: int
        The index of the word in it's respective sentence.
    start_time: float
        Time in seconds for when this word begins.
    end_time: float
        Time in seconds for when this word ends.
    text: str
        The raw text of the word, lowercased and cleaned of all non-deliminating chars.
    annotations: Optional[Dict[str, Any]]
        Any annotations specific to this word.
        Default: None (no annotations)
    """

    index: int
    start_time: float
    end_time: float
    text: str
    annotations: Optional[Dict[str, Any]]


@dataclass_json
@dataclass
class Sentence:
    """
    Data for a sentence in a transcript.

    Parameters
    ----------
    index: int
        The index of the sentence in it's respective transcript.
    confidence: float
        A number between 0 and 1 for the confidence of the sentence accuracy.
    start_time: float
        Time in seconds for when this sentence begins.
    end_time: float
        Time in seconds for when this sentence ends.
    speaker_index: Optional[int]
        The optional speaker index for the sentence.
    speaker_name: Optional[str]
        The optional speaker name for the sentence.
    annotations: Optional[Dict[str, Any]]
        Any annotations specific to this sentence.
        Default: None (no annotations)
    words: List[Word]
        The list of word for the sentence.
        See Word model for more info.
    text: str
        The text of the sentence including all formatting and non-deliminating chars.
    """

    index: int
    confidence: float
    start_time: float
    end_time: float
    words: List[Word]
    text: str
    speaker_index: Optional[int] = None
    speaker_name: Optional[str] = None
    annotations: Optional[Dict[str, Any]] = None


@dataclass_json
@dataclass
class Transcript:
    """
    Transcript model for all transcripts in CDP databases / filestores.

    Parameters
    ----------
    confidence: float
        A number between 0 and 1.
        If available, use the average of all confidence annotations reported for each
        text block in the transcript.
        Otherwise, make an estimation for (or manually calculate):
        `n-correct-tokens / n-total-tokens` for the whole transcript.
    generator: str
        A descriptive name of the generative process that produced this transcript.
        Example: "Google Speech-to-Text -- Lib Version: 2.0.1"
    session_datetime: Optional[str]
        ISO formatted datetime for the session that this document transcribes.
    created_datetime: str
        ISO formatted datetime for when this transcript was created.
    sentences: List[Sentence]
        A list of sentences.
        See Sentence documentation for more information.
    annotations: Optional[Dict[str, Any]]
        Any annotations that can be applied to the whole transcript.
        Default: None (no annotations)
        See TranscriptAnnotations for list of known annotations and their dtypes.


    Examples
    --------
    Dumping transcript to JSON file.

    >>> # transcript = Transcript(...)
    ... with open("transcript.json", "w") as open_resource:
    ...     open_resource.write(transcript.to_json())

    Reading transcript from JSON file.

    >>> with open("transcript.json", "r") as open_resource:
    ...     transcript = Transcript.from_json(open_resource.read())
    """

    confidence: float
    generator: str
    session_datetime: Optional[str]
    created_datetime: str
    sentences: List[Sentence]
    annotations: Optional[Dict[str, Any]] = None


###############################################################################
# Annotation Definitions
#
# Developers please document any annotation you wish to add.
# Docstrings for constants go _after_ the constant.


class TranscriptAnnotations(Enum):
    """
    Annotations that can appear (but are not guaranteed) for the whole transcript.
    """


class TextBlockAnnotations(Enum):
    """
    Annotations that can appear (but are not guaranteed) on any transcript text block.

    Examples
    --------
    Usage pattern for annotation attachment.

    >>> text_block_annotations = {}
    ... text_block_annotations[TextBlockAnnotations.confidence.name] = 0.9421
    """

    confidence = float
    """
    A number between 0 and 1.

    Notes
    -----
    Most speech-to-text models report confidence values. For more information:
    https://cloud.google.com/speech-to-text/docs/basics#confidence-values
    """


###############################################################################


EXAMPLE_TRANSCRIPT = Transcript(
    confidence=0.93325,
    generator="JacksonGen -- Lib Version: 0.0.0",
    session_datetime=datetime(2021, 1, 10, 15).isoformat(),
    created_datetime=datetime.utcnow().isoformat(),
    sentences=[
        Sentence(
            index=0,
            text="Hello everyone.",
            confidence=0.9,
            start_time=0.0,
            end_time=1.0,
            speaker_name="Jackson Maxfield Brown",
            speaker_index=0,
            words=[
                Word(
                    index=0,
                    start_time=0.0,
                    end_time=0.5,
                    text="hello",
                    annotations=None,
                ),
                Word(
                    index=1,
                    start_time=0.5,
                    end_time=1.0,
                    text="everyone",
                    annotations=None,
                ),
            ],
            annotations={
                TextBlockAnnotations.confidence.name: 0.987,
            },
        ),
        Sentence(
            index=1,
            text="Hi all.",
            confidence=0.95,
            start_time=1.0,
            end_time=2.0,
            speaker_name="Isaac Na",
            speaker_index=1,
            words=[
                Word(
                    index=0,
                    start_time=1.0,
                    end_time=1.5,
                    text="hi",
                    annotations=None,
                ),
                Word(
                    index=1,
                    start_time=1.5,
                    end_time=2.0,
                    text="all",
                    annotations=None,
                ),
            ],
            annotations={
                TextBlockAnnotations.confidence.name: 0.987,
            },
        ),
    ],
)
