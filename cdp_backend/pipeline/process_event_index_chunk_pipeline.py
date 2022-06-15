#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
from typing import Dict, List, NamedTuple, Union

import fireo
import pandas as pd
from prefect import Flow, task, unmapped

from ..database import functions as db_functions
from ..database import models as db_models
from ..file_store import functions as fs_functions
from .generate_event_index_pipeline import REMOTE_INDEX_CHUNK_DIR
from .pipeline_config import EventIndexPipelineConfig

###############################################################################


class AlmostCompleteIndexedEventGram(NamedTuple):
    event_id: str
    unstemmed_gram: str
    stemmed_gram: str
    context_span: str
    value: float
    datetime_weighted_value: float


@task
def pull_chunk(
    credentials_file: str,
    bucket_name: str,
    filename: str,
) -> str:
    return fs_functions.download_file(
        credentials_file=credentials_file,
        bucket=bucket_name,
        remote_filepath=filename,
        save_path=filename,
    )


@task
def chunk_n_grams(
    chunk_path: str,
    upload_batch_size: int = 500,
) -> List[List[AlmostCompleteIndexedEventGram]]:
    """
    Split the large n_grams dataframe into multiple lists of IndexedEventGram models
    for batched, mapped, upload.
    """
    # Read index chunk
    n_grams_df = pd.read_parquet(chunk_path)

    # Split single large dataframe into many dataframes
    n_grams_dfs = [
        n_grams_df[i : i + upload_batch_size]
        for i in range(0, n_grams_df.shape[0], upload_batch_size)
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


def create_event_index_upload_pipeline(
    config: EventIndexPipelineConfig,
    index_chunk: Union[str, Path],
    upload_batch_size: int = 500,
) -> Flow:
    """
    Create the Prefect Flow object to preview, run, or visualize for uploading a
    generated index for all events in the database.

    Parameters
    ----------
    config: EventIndexPipelineConfig
        Configuration options for the pipeline.
    n_grams: int
        N number of terms to act as a unique entity. Default: 1
    upload_batch_size: int
        Number of ngrams to upload to database in a single batch.
        Default: 500 (max)

    Returns
    -------
    flow: Flow
        The constructed CDP Event Index Pipeline as a Prefect Flow.
    """
    with Flow("CDP Event Index Pipeline") as flow:
        # Pull the file
        index_chunk_local = pull_chunk(
            credentials_file=config.google_credentials_file,
            bucket_name=config.validated_gcs_bucket_name,
            filename=f"{REMOTE_INDEX_CHUNK_DIR}/{index_chunk}",
        )

        # Route to remote database storage
        chunked_scored_n_grams = chunk_n_grams(
            index_chunk_local,
            upload_batch_size=upload_batch_size,
        )
        store_n_gram_chunk.map(
            n_gram_chunk=chunked_scored_n_grams,
            credentials_file=unmapped(config.google_credentials_file),
        )

    return flow
