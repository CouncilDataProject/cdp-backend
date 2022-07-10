#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from dataclasses_json import dataclass_json

###############################################################################
# Annotation Definitions
#
# Developers please document any annotation you wish to add.
# Docstrings for constants go _after_ the constant.


@dataclass_json
@dataclass
class WordAnnotations:
    """
    Annotations that can appear on an individual word level.
    """


@dataclass_json
@dataclass
class SentenceAnnotations:
    """
    Annotations that can appear on an individual sentence level.
    """


@dataclass_json
@dataclass
class SectionAnnotation:
    """
    A section annotation used for topic segmentation and minutes item alignment.

    Parameters
    ----------
    name: str
        The name of the sections.
    start_sentence_index: int
        The sentence index that acts as the starting point for the section.
    stop_sentence_index: int
        The sentence index that acts as the stopping point for the section.
    generator: str
        A description of the algorithm or annotator that provided this annotation.
    description: Optional[str]
        An optional description of what the section is about.
        Default: None

    Notes
    -----
    The attributes `start_sentence_index` and `stop_sentence_index` should be treated
    as inclusive and exclusive respectively, exactly like how the Python `slice`
    function works.

    I.e. given a transcript of ordered sentences, the sentence indices will work
    as the parameters for a slice against the list of sentences:
    `sentences[start_sentence_index:stop_sentence_index]`

    Examples
    --------
    Usage pattern for annotation attachment.

    >>> transcript.annotations.sections = [
    ...     SectionAnnotation(
    ...         name="Public Comment",
    ...         start_sentence_index=12,
    ...         stop_sentence_index=87,
    ...         generator="Jackson Maxfield Brown",
    ...     ),
    ...     SectionAnnotation(
    ...         name="CB 120121",
    ...         start_sentence_index=243,
    ...         stop_sentence_index=419,
    ...         description="AN ORDINANCE relating to land use and zoning ...",
    ...         generator="queue-cue--v1.0.0",
    ...     ),
    ... ]
    """

    name: str
    start_sentence_index: int
    stop_sentence_index: Optional[int]
    generator: str
    description: Optional[str] = None


@dataclass_json
@dataclass
class TranscriptAnnotations:
    """
    Annotations that can appear (but are not guaranteed) for the whole transcript.
    """

    sections: Optional[List[SectionAnnotation]] = None


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
    annotations: Optional[WordAnnotations]
        Any annotations specific to this word.
        Default: None (no annotations)
    """

    index: int
    start_time: float
    end_time: float
    text: str
    annotations: Optional[WordAnnotations] = None


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
    annotations: Optional[SentenceAnnotations]
        Any annotations specific to this sentence.
        Default: None (no annotations)
    words: List[Word]
        The list of word for the sentence.
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
    annotations: Optional[SentenceAnnotations] = None


@dataclass_json
@dataclass
class Transcript:
    """
    Transcript model for all transcripts in CDP databases / filestores.

    Parameters
    ----------
    generator: str
        A descriptive name of the generative process that produced this transcript.
        Example: "Google Speech-to-Text -- Lib Version: 2.0.1"
    confidence: float
        A number between 0 and 1.
        If available, use the average of all confidence annotations reported for each
        text block in the transcript.
        Otherwise, make an estimation for (or manually calculate):
        `n-correct-tokens / n-total-tokens` for the whole transcript.
    session_datetime: Optional[str]
        ISO formatted datetime for the session that this document transcribes.
    created_datetime: str
        ISO formatted datetime for when this transcript was created.
    sentences: List[Sentence]
        A list of sentences.
    annotations: Optional[TranscriptAnnotations]
        Any annotations that can be applied to the whole transcript.
        Default: None (no annotations)

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

    generator: str
    confidence: float
    session_datetime: Optional[str]
    created_datetime: str
    sentences: List[Sentence]
    annotations: Optional[TranscriptAnnotations] = None

    def __repr__(self) -> str:
        output = "Transcript("

        # Use vars to maintain subclassing
        for k, v in vars(self).items():
            # Truncate sentences
            if k == "sentences":
                output += f"{k}=[...] (n={len(v)}), "

            # Add quotes for strings
            elif type(v) == str:
                output += f"{k}='{v}', "

            else:
                output += f"{k}={v}, "

        # Remove last comma and space and close parentheses
        return output[:-2] + ")"


###############################################################################


EXAMPLE_TRANSCRIPT = Transcript(
    generator="JacksonGen -- Lib Version: 0.0.0",
    confidence=0.93325,
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
                ),
                Word(
                    index=1,
                    start_time=0.5,
                    end_time=1.0,
                    text="everyone",
                ),
            ],
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
                ),
                Word(
                    index=1,
                    start_time=1.5,
                    end_time=2.0,
                    text="all",
                ),
            ],
        ),
    ],
    annotations=TranscriptAnnotations(
        sections=[
            SectionAnnotation(
                name="Call to Order",
                start_sentence_index=0,
                stop_sentence_index=2,
                generator="Jackson Maxfield Brown",
            )
        ],
    ),
)
