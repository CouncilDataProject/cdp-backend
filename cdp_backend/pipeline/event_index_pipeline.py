#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, List, NamedTuple, Tuple

import fireo
import pandas as pd
import pytz
import rapidfuzz
from dataclasses_json import dataclass_json
from gcsfs import GCSFileSystem
from nltk import ngrams
from nltk.stem import SnowballStemmer
from prefect import Flow, task, unmapped

from ..database import functions as db_functions
from ..database import models as db_models
from ..utils import string_utils
from .pipeline_config import EventIndexPipelineConfig
from .transcript_model import Sentence, Transcript

###############################################################################

log = logging.getLogger(__name__)

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
    # Fetch all transcripts
    # This comes with references to Session and File models
    # Session models come with reference to Event model
    # Event models come with reference to Body model
    return db_functions.get_all_of_collection(
        db_model=db_models.Transcript,
        credentials_file=credentials_file,
    )


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
        referenced_session_id = transcript.session_ref.ref.id
        if referenced_session_id not in selected_transcripts:
            selected_transcripts[referenced_session_id] = transcript

        # Multiple transcripts for a single session
        # pick the higher confidence
        elif (
            transcript.confidence
            > selected_transcripts[referenced_session_id].confidence
        ):
            selected_transcripts[referenced_session_id] = transcript

    return list(selected_transcripts.values())


class EventTranscripts(NamedTuple):
    event_id: str
    event_datetime: datetime
    transcript_db_files: List[db_models.File]


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
        session = transcript.session_ref.get()
        referenced_event_id = session.event_ref.ref.id
        if referenced_event_id not in event_transcripts:
            event_transcripts[referenced_event_id] = EventTranscripts(
                event_id=referenced_event_id,
                event_datetime=session.event_ref.get().event_datetime,
                transcript_db_files=[transcript.file_ref.get()],
            )

        # Update existing event_transcripts object
        else:
            event_transcripts[referenced_event_id].transcript_db_files.append(
                transcript.file_ref.get()
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
    # We attach the id for simpler gram grouping
    # We attach the datetime for simpler datetime weighting
    event_id: str
    event_datetime: datetime
    unstemmed_gram: str
    stemmed_gram: str
    context_span: str


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
    for transcript_db_file in event_transcripts.transcript_db_files:
        with TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            local_transcript_filepath = temp_dir_path / transcript_db_file.name

            # Download transcript
            fs.get(
                rpath=transcript_db_file.uri,
                lpath=str(local_transcript_filepath),
            )

            # Init transcript
            with open(local_transcript_filepath, "r") as open_f:
                transcript = Transcript.from_json(open_f.read())  # type: ignore

            # Get cleaned sentences by removing stop words
            cleaned_sentences: List[SentenceManager] = [
                SentenceManager(
                    original_details=sentence,
                    cleaned_text=string_utils.clean_text(
                        sentence.text,
                        clean_stop_words=True,
                        clean_emojis=True,
                    ),
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

                    # Get context span
                    # Because ngrams function, cleaning, and split may affect the exact
                    # matchup of the term, use fuzzy diff to find closest
                    closest_term = ""
                    closest_term_score = 0.0
                    for term in sm.original_details.text.split():
                        similarity = rapidfuzz.fuzz.QRatio(term, n_gram[0])
                        if similarity > closest_term_score:
                            closest_term = term
                            closest_term_score = similarity

                    # Get surrounding terms
                    terms = sm.original_details.text.split()
                    target_term_index = terms.index(closest_term)

                    # Get left and right indices
                    left_i = 0 if target_term_index - 8 < 0 else target_term_index - 8
                    right_i = (
                        None
                        if target_term_index + 7 >= len(terms) - 1
                        else target_term_index + 7
                    )
                    context_span = " ".join(terms[left_i:right_i])

                    # Append ellipsis
                    if left_i != 0:
                        context_span = f"... {context_span}"
                    if right_i is not None:
                        context_span = f"{context_span}..."

                    # Append to event list
                    event_n_grams.append(
                        ContextualizedGram(
                            event_id=event_transcripts.event_id,
                            event_datetime=event_transcripts.event_datetime,
                            unstemmed_gram=unstemmed_n_gram,
                            stemmed_gram=stemmed_n_gram,
                            context_span=context_span,
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
            n_gram.to_dict()  # type: ignore
            for single_event_n_grams in all_events_n_grams
            for n_gram in single_event_n_grams
        ]
    )


@task
def compute_tfidf(
    n_grams: pd.DataFrame,
    datetime_weighting_days_decay: int = 30,
) -> pd.DataFrame:
    """
    Compute term frequencies, inverse document frequencies, tfidf, and weighted tfidf
    values for each n_gram in the dataframe.
    """
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
    UTCNOW = datetime.utcnow()
    UTCNOW = pytz.timezone("UTC").localize(UTCNOW)
    n_grams["datetime_weighted_tfidf"] = n_grams.apply(
        # Unit of decay is in months (`/ 30`)
        # `+ 2` protects against divison by zero
        lambda row: row.tfidf
        / math.log(
            ((UTCNOW - row.event_datetime).days / datetime_weighting_days_decay) + 2
        ),
        axis=1,
    )

    return n_grams


@task
def store_local_index(n_grams_df: pd.DataFrame, n_grams: int) -> None:
    n_grams_df.to_parquet(f"tfidf-{n_grams}.parquet")


class AlmostCompleteIndexedEventGram(NamedTuple):
    event_id: str
    unstemmed_gram: str
    stemmed_gram: str
    context_span: str
    value: float
    datetime_weighted_value: float


@task
def chunk_n_grams(
    n_grams_df: pd.DataFrame,
) -> List[List[AlmostCompleteIndexedEventGram]]:
    """
    Split the large n_grams dataframe into multiple lists of IndexedEventGram models
    for batched, mapped, upload.
    """
    # Split single large dataframe into many dataframes
    chunk_size = 400
    n_grams_dfs = [
        n_grams_df[i : i + chunk_size]
        for i in range(0, n_grams_df.shape[0], chunk_size)
    ]

    # Convert each dataframe into a list of indexed event gram
    event_gram_chunks: List[List[AlmostCompleteIndexedEventGram]] = []
    for n_gram_df_chunk in n_grams_dfs:
        event_gram_chunk: List[AlmostCompleteIndexedEventGram] = []
        for _, row in n_gram_df_chunk.iterrows():
            event_gram_chunk.append(
                AlmostCompleteIndexedEventGram(
                    event_id=row.event_id,
                    unstemmed_gram=row.unstemmed_gram,
                    stemmed_gram=row.stemmed_gram,
                    context_span=row.context_span,
                    value=row.tfidf,
                    datetime_weighted_value=row.datetime_weighted_tfidf,
                )
            )

        event_gram_chunks.append(event_gram_chunk)

    return event_gram_chunks


@task
def store_n_gram_chunk(
    n_gram_chunk: List[AlmostCompleteIndexedEventGram],
    credentials_file: str,
) -> None:
    """
    Write all IndexedEventGrams in a single batch.

    This isn't about an atomic batch but reducing the total upload time.
    """
    # Init batch
    batch = fireo.batch()

    # Trigger upserts for all items
    event_lut: Dict[str, db_models.Event] = {}
    for almost_complete_ieg in n_gram_chunk:
        if almost_complete_ieg.event_id not in event_lut:
            event_lut[almost_complete_ieg.event_id] = db_models.Event.collection.get(
                f"{db_models.Event.collection_name}/{almost_complete_ieg.event_id}"
            )

        # Construct true ieg
        ieg = db_models.IndexedEventGram()
        ieg.event_ref = event_lut[almost_complete_ieg.event_id]
        ieg.unstemmed_gram = almost_complete_ieg.unstemmed_gram
        ieg.stemmed_gram = almost_complete_ieg.stemmed_gram
        ieg.context_span = almost_complete_ieg.context_span
        ieg.value = almost_complete_ieg.value
        ieg.datetime_weighted_value = almost_complete_ieg.datetime_weighted_value

        db_functions.upload_db_model(
            db_model=ieg,
            credentials_file=credentials_file,
            batch=batch,
        )

    # Commit
    batch.commit()


def create_event_index_pipeline(
    config: EventIndexPipelineConfig,
    n_grams: int = 1,
    store_local: bool = False,
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
    store_local: bool
        Should the generated index be stored locally to disk or uploaded to database.
        Storing the local index is useful for testing search result rankings with the
        `search_cdp_events` bin script.
        Default: False (store to database)

    Returns
    -------
    flow: Flow
        The constructed CDP Event Index Pipeline as a Prefect Flow.
    """
    with Flow("CDP Event Index Pipeline") as flow:
        # Ensure stopwords are downloaded
        # Do this once to ensure that we don't enter a race condition
        # with multiple workers trying to download / read overtop one another
        # later on.
        try:
            from nltk.corpus import stopwords

            stopwords.words("english")
        except LookupError:
            import nltk

            nltk.download("stopwords")
            log.info("Downloaded nltk stopwords")
            from nltk.corpus import stopwords

            stopwords.words("english")

        # Get all transcripts
        all_transcripts = get_transcripts(
            credentials_file=config.google_credentials_file
        )

        # Select highest confidence transcript for each session
        selected_transcripts = get_highest_confidence_transcript_for_each_session(
            transcripts=all_transcripts
        )

        # Get all transcripts for each event (multi-session events)
        event_transcripts = get_transcripts_per_event(transcripts=selected_transcripts)

        # Read all transcripts for each event and generate grams
        all_event_transcript_n_grams = read_transcripts_and_generate_grams.map(
            event_transcripts=event_transcripts,
            n_grams=unmapped(n_grams),
            credentials_file=unmapped(config.google_credentials_file),
        )

        # Convert to dataframe for tfidf calc
        all_events_n_grams = convert_all_n_grams_to_dataframe(
            all_events_n_grams=all_event_transcript_n_grams,
        )

        # Weighted n grams by tfidf
        scored_n_grams = compute_tfidf(
            n_grams=all_events_n_grams,
            datetime_weighting_days_decay=config.datetime_weighting_days_decay,
        )

        # Route to local storage task or remote bulk upload
        if store_local:
            store_local_index(n_grams_df=scored_n_grams, n_grams=n_grams)

        # Route to remote database storage
        else:
            chunked_scored_n_grams = chunk_n_grams(scored_n_grams)
            store_n_gram_chunk.map(
                n_gram_chunk=chunked_scored_n_grams,
                credentials_file=unmapped(config.google_credentials_file),
            )

    return flow
