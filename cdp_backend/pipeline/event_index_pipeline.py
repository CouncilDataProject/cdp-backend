#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import math
import re
import string
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, List, NamedTuple, Tuple

import fireo
import pandas as pd
import pytz
from dataclasses_json import dataclass_json
from gcsfs import GCSFileSystem
from nltk import ngrams
from nltk.stem import SnowballStemmer
from prefect import Flow, task, unmapped

from ..database import models as db_models
from .pipeline_config import EventIndexPipelineConfig
from .transcript_model import Sentence, Transcript

###############################################################################

log = logging.getLogger(__name__)

# Ensure stopwords are downloaded
try:
    from nltk.corpus import stopwords

    STOPWORDS = stopwords.words("english")
except LookupError:
    import nltk

    nltk.download("stopwords")
    log.info("Downloaded nltk stopwords")
    from nltk.corpus import stopwords

    STOPWORDS = stopwords.words("english")

###############################################################################


@task
def get_transcripts(credentials_file: str) -> List[db_models.Transcript]:
    """
    Initialize fireo connection and pull all Transcript models.

    Parameters
    ----------
    credentials_file: str
        Path to Google Service Account Credentials JSON file.

    Returns
    -------
    transcripts: List[db_models.Transcript]
        All transcript documents found in the database.

    Notes
    -----
    This _can_ become a dangerous operation if the database has millions of transcript
    documents as this will additionally pull all referenced Event, Session, Body,
    and File database models.
    """
    fireo.connection(from_file=credentials_file)

    # Fetch all transcripts
    # This comes with references to Session and File models
    # Session models come with reference to Event model
    # Event models come with reference to Body model
    return list(db_models.Transcript.collection.fetch(limit=int(1e9)))


@task
def get_highest_confidence_transcript_for_each_session(
    transcripts: List[db_models.Transcript],
) -> List[db_models.Transcript]:
    """
    Filter down a list transcript documents to just a single transcript
    per session taking the highest confidence transcript document.

    Parameters
    ----------
    transcripts: List[db_models.Transcript]
        List of transcript database documents.

    Returns
    -------
    transcripts: List[db_models.Transcript]
        Filtered list of transcript database documents where only a single transcript
        exists for each referenced session.
    """
    # We can't use pandas groupby because sessions objects can't be naively compared
    # Instead we create a Dict of session id to document model
    # We update as we iterate through list of all transcripts
    selected_transcripts: Dict[str, pd.Series] = {}
    for transcript in transcripts:
        if transcript.session_ref.id not in selected_transcripts:
            selected_transcripts[transcript.session_ref.id] = transcript

        # Multiple transcripts for a single session
        # pick the higher confidence
        elif (
            transcript.confidence
            > selected_transcripts[transcript.session_ref.id].confidence
        ):
            selected_transcripts[transcript.session_ref.id] = transcript

    return list(selected_transcripts.values())


class EventTranscripts(NamedTuple):
    event: db_models.Event
    transcripts: List[db_models.Transcript]


@task
def get_transcripts_per_event(
    transcripts: List[db_models.Transcript],
) -> List[EventTranscripts]:
    """
    Group all transcripts related to a single event together into
    EventTranscripts objects.
    """
    # Create event transcripts as event id mapped to EventTranscripts object
    event_transcripts: Dict[str, EventTranscripts] = {}
    for transcript in transcripts:
        # Add new event
        if transcript.session_ref.event_ref.id not in event_transcripts:
            event_transcripts[transcript.session_ref.event_ref.id] = EventTranscripts(
                event=transcript.session_ref.event_ref,
                transcripts=[transcript],
            )

        # Update existing eventtranscripts object
        else:
            event_transcripts[transcript.session_ref.event_ref.id].transcripts.append(
                transcript
            )

    return list(event_transcripts.values())


@dataclass_json
@dataclass
class SentenceManager:
    original_details: Sentence
    cleaned_text: str
    n_grams: List[Tuple[str]]


@dataclass_json
@dataclass
class ContextualizedGram:
    event_id: str
    event_datetime: datetime
    unstemmed_gram: str
    stemmed_gram: str
    context_span: str


def clean_text(text: str) -> str:
    # Remove new line and tab characters
    cleaned_formatting = text.replace("\n", " ").replace("\t", " ")

    # Remove punctuation except periods
    cleaned_punctuation = re.sub(
        f"[{re.escape(string.punctuation)}]", "", cleaned_formatting
    )

    # Remove stopwords
    joined_stopwords = "|".join(STOPWORDS)
    cleaned_stopwords = re.sub(
        r"\b(" + joined_stopwords + r")\b",
        "",
        cleaned_punctuation,
    )

    # Remove gaps in string
    try:
        cleaned_doc = re.sub(r" {2,}", " ", cleaned_stopwords)
        if cleaned_doc[0] == " ":
            cleaned_doc = cleaned_doc[1:]
        if cleaned_doc[-1] == " ":
            cleaned_doc = cleaned_doc[:-1]

    # IndexError occurs when the string was cleaned and it contained entirely stop
    # words or punctuation for some reason
    except IndexError:
        return ""

    return cleaned_doc


@task
def read_transcripts_and_generate_grams(
    event_transcripts: EventTranscripts, n_grams: int, credentials_file: str
) -> List[ContextualizedGram]:
    """
    Parse all documents and create a list of contextualized grams for later weighting.

    Parameters
    ----------
    event_transcripts: EventTranscripts
        The EventTranscripts object to parse all transcripts for.
    n_grams: int
        N number of terms to act as a unique entity.
    credentials_file: str
        Path to Google Service Account Credentials JSON file.

    Returns
    -------
    grams: List[ContextualizedGram]
        All grams found in all transcripts provided.
    """
    fs = GCSFileSystem(token=credentials_file)

    # Store all n_gram results
    event_n_grams: List[ContextualizedGram] = []

    # Iter over each transcript
    for transcript in event_transcripts.transcripts:
        with TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            local_transcript_filepath = temp_dir_path / transcript.file_ref.name

            # Download transcript
            fs.get(
                rpath=transcript.file_ref.uri,
                lpath=str(local_transcript_filepath),
            )

            # Init transcript
            with open(local_transcript_filepath, "r") as open_f:
                transcript = Transcript.from_json(open_f.read())

            # Get cleaned sentences by removing stop words
            cleaned_sentences: List[SentenceManager] = [
                SentenceManager(
                    original_details=sentence,
                    cleaned_text=clean_text(sentence.text),
                    n_grams=[],
                )
                for sentence in transcript.sentences
            ]

            # Filter any empty sentences
            cleaned_sentences = [
                sm for sm in cleaned_sentences if len(sm.cleaned_text) > 1
            ]

            # Get all n_grams for each sentence
            for sm in cleaned_sentences:
                sm.n_grams = [*ngrams(sm.cleaned_text.split(), n_grams)]

            # Init stemmer and stem all grams
            stemmer = SnowballStemmer("english")
            for sm in cleaned_sentences:
                for n_gram in sm.n_grams:
                    # Join into a single n gram
                    unstemmed_n_gram = " ".join(n_gram)

                    # Join, lower, and stem the n gram
                    stemmed_n_gram = " ".join(
                        [stemmer.stem(term.lower()) for term in n_gram]
                    )

                    # Append to event list
                    event_n_grams.append(
                        ContextualizedGram(
                            event_id=event_transcripts.event.id,
                            event_datetime=event_transcripts.event.event_datetime,
                            unstemmed_gram=unstemmed_n_gram,
                            stemmed_gram=stemmed_n_gram,
                            context_span=sm.original_details.text[:128].strip(),
                        )
                    )

    return event_n_grams


@task
def convert_all_n_grams_to_dataframe(
    all_events_n_grams: List[List[ContextualizedGram]],
) -> pd.DataFrame:
    """
    Flatten all n grams from all events into one single dataframe.
    """
    return pd.DataFrame(
        [
            n_gram.to_dict()
            for single_event_n_grams in all_events_n_grams
            for n_gram in single_event_n_grams
        ]
    )


@task
def compute_tfidf(n_grams: pd.DataFrame) -> pd.DataFrame:
    """
    Compute term frequencies, inverse document frequencies, tfidf, and weighted tfidf
    values for each n_gram in the dataframe.
    """
    # Get farthest back datetime and timezone localized UTC now
    # These will be used for creating the datetime_weighted_tfidf values
    DATETIME_BEGIN = datetime(1970, 1, 1, tzinfo=pytz.timezone("UTC"))
    UTCNOW = datetime.utcnow()
    UTCNOW = pytz.timezone("UTC").localize(UTCNOW)
    TIMEDELTA_NOW = (UTCNOW - DATETIME_BEGIN).total_seconds()

    # Get term frequencies
    n_grams["tf"] = n_grams.groupby(
        ["event_id", "stemmed_gram"]
    ).stemmed_gram.transform("count")

    # Drop duplicates for inverse-document-frequencies
    n_grams = n_grams.drop_duplicates(["event_id", "stemmed_gram"])

    # Get idf
    N = len(n_grams.event_id.unique())
    n_grams["idf"] = (
        n_grams.groupby("stemmed_gram")
        .event_id.transform("count")
        .apply(lambda df: math.log(N / df))
    )

    # Store tfidf
    n_grams["tfidf"] = n_grams.tf * n_grams.idf

    # Drop terms worth nothing
    n_grams = n_grams[n_grams.tfidf != 0]

    # Add datetime weighted tfidf
    n_grams["datetime_weighted_tfidf"] = n_grams.apply(
        lambda row: row.tfidf
        / math.log(
            TIMEDELTA_NOW - (row.event_datetime - DATETIME_BEGIN).total_seconds()
        ),
        axis=1,
    )

    return n_grams


@task
def store_tfidf(df: pd.DataFrame, n_grams: int):
    df.to_parquet(f"tfidf-{n_grams}.parquet")


def create_event_index_pipeline(
    config: EventIndexPipelineConfig,
    n_grams: int = 1,
) -> Flow:
    """
    Create the Prefect Flow object to preview, run, or visualize for indexing
    all events in the database.

    Parameters
    ----------
    config: EventIndexPipelineConfig
        Configuration options for the pipeline.
    n_grams: int
        N number of terms to act as a unique entity. Default: 1

    Returns
    -------
    flow: Flow
        The constructed CDP Event Index Pipeline as a Prefect Flow.
    """
    with Flow("CDP Event Index Pipeline") as flow:
        # Get all transcripts
        all_transcripts = get_transcripts(
            credentials_file=config.google_credentials_file
        )

        # Select highest confidence transcript for each session
        selected_transcripts = get_highest_confidence_transcript_for_each_session(
            transcripts=all_transcripts
        )

        # Get all transcripts for each event (multi-session events)
        event_transcripts = get_transcripts_per_event(selected_transcripts)

        # Read all transcripts for each event and generate grams
        all_event_transcript_n_grams = read_transcripts_and_generate_grams.map(
            event_transcripts=event_transcripts,
            n_grams=unmapped(n_grams),
            credentials_file=unmapped(config.google_credentials_file),
        )

        # Convert to dataframe for tfidf calc
        all_events_n_grams = convert_all_n_grams_to_dataframe(
            all_event_transcript_n_grams,
        )

        # Weighted n grams by tfidf
        scored_n_grams = compute_tfidf(all_events_n_grams)

        store_tfidf(scored_n_grams, n_grams=n_grams)

    return flow
