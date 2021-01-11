#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from dataclasses_json import dataclass_json

###############################################################################


@dataclass_json
@dataclass
class TextBlockData:
    """
    Text block data for a transcript.

    Parameters
    ----------
    text: str
        The full text portion of this data block.
    start_time: float
        Time in seconds for when this block of data begins.
    end_time: float
        Time in seconds for when this block of data ends.
    speaker: Optional[str]
        The speaker identifier for this text block.
        Default: None (No speaker identifier available)
    annotations: Optional[Dict[str, Any]]
        Any annotations specific to this text block.
        Default: None (no annotations)
        See TextBlockAnnotations for list of known annotations and their dtypes.
    """

    text: str
    start_time: float
    end_time: float
    speaker: Optional[str] = None
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
    session_datetime: str
        ISO formatted datetime for the session that this document transcribes.
    created_datetime: str
        ISO formatted datetime for when this transcript was created.
    data: List[TextBlockData]
        A list of text blocks.
        See TextBlockData documentation for more information.
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
    session_datetime: str
    created_datetime: str
    data: List[TextBlockData]
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
    session_datetime=(datetime.utcnow() - timedelta(hours=3)).isoformat(),
    created_datetime=datetime.utcnow().isoformat(),
    data=[
        TextBlockData(
            text="Hello everyone.",
            start_time=0.0,
            end_time=1.0,
            speaker="Jackson Maxfield Brown",
            annotations={
                TextBlockAnnotations.confidence.name: 0.987,
            },
        ),
        TextBlockData(
            text="Hey!",
            start_time=1.2,
            end_time=1.4,
            speaker="Isaac Na",
            annotations={
                TextBlockAnnotations.confidence.name: 0.912,
            },
        ),
        TextBlockData(
            text="Hello!",
            start_time=1.6,
            end_time=1.9,
            speaker="To Huynh",
            annotations={
                TextBlockAnnotations.confidence.name: 0.999,
            },
        ),
        TextBlockData(
            text="Who is speaking this?",
            start_time=2.2,
            end_time=3.9,
            annotations={
                TextBlockAnnotations.confidence.name: 0.835,
            },
        ),
    ],
)
