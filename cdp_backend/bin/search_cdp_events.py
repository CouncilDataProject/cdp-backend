#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, List, NamedTuple

import dask.dataframe as dd
import fireo
from google.auth.credentials import AnonymousCredentials
from google.cloud.firestore import Client
from nltk import ngrams
from nltk.stem import SnowballStemmer

from cdp_backend.database import models as db_models
from cdp_backend.utils.string_utils import clean_text

###############################################################################

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)4s: %(module)s:%(lineno)4s %(asctime)s] %(message)s",
)
log = logging.getLogger(__name__)

###############################################################################


class SearchSortByField(NamedTuple):
    name: str
    local_field: str
    remote_field: str


DATETIME_WEIGHTED_RELEVANCE = SearchSortByField(
    name="datetime_weighted_relevance",
    local_field="datetime_weighted_tfidf",
    remote_field="datetime_weighted_value",
)

RELEVANCE = SearchSortByField(
    name="relevance",
    local_field="tfidf",
    remote_field="value",
)

###############################################################################


class Args(argparse.Namespace):
    def __init__(self) -> None:
        self.__parse()

    def __parse(self) -> None:
        p = argparse.ArgumentParser(
            prog="search_cdp_events", description="Search CDP events given a query."
        )

        p.add_argument(
            "instance",
            type=str,
            help="Which instance to query.",
        )
        p.add_argument(
            "-q",
            "--query",
            type=str,
            default="residential zoning and housing affordability",
            help="Query to search with.",
        )
        p.add_argument(
            "-s",
            "--sort_by",
            type=str,
            default=DATETIME_WEIGHTED_RELEVANCE.name,
            choices=[DATETIME_WEIGHTED_RELEVANCE.name, RELEVANCE.name],
            help="Choice between datetime weighted and pure relevance (TFIDF score).",
        )
        p.add_argument(
            "-f",
            "--first",
            type=int,
            default=4,
            help="Number of results to return.",
        )
        p.add_argument(
            "-l",
            "--local_index_glob",
            type=str,
            default="tfidf-*.parquet",
            help="The file glob for which files to use for reading a planned index.",
        )
        p.parse_args(namespace=self)


###############################################################################


def get_stemmed_grams_from_query(query: str) -> List[str]:
    # Spawn stemmer
    stemmer = SnowballStemmer("english")

    # Create stemmed grams for query
    query_terms = clean_text(query, clean_stop_words=True).split()
    stemmed_grams = []
    for n_gram_size in [1, 2, 3]:
        grams = ngrams(query_terms, n_gram_size)
        for gram in grams:
            stemmed_grams.append(" ".join(stemmer.stem(term.lower()) for term in gram))

    return stemmed_grams


def _query_event_index(
    stemmed_gram: str,
) -> List[db_models.IndexedEventGram]:
    # Filter for stemmed gram
    filtered_set = db_models.IndexedEventGram.collection.filter(
        "stemmed_gram", "==", stemmed_gram
    )
    return list(filtered_set.fetch(limit=int(1e9)))


class EventMatch(NamedTuple):
    event: db_models.Event
    pure_relevance: float
    datetime_weighted_relevance: float
    contained_grams: List[str]
    selected_context_span: str
    keywords: List[str]


def run_remote_search(query: str, sort_by: str, first: int = 4) -> None:
    log.info("Running search against remote index...")

    # Get stemmed grams
    stemmed_grams = get_stemmed_grams_from_query(query=query)

    # Begin timer
    start_dt = datetime.utcnow()

    # Get all matching ieg models
    with ThreadPoolExecutor() as exe:
        all_gram_results = list(
            exe.map(
                _query_event_index,
                stemmed_grams,
            )
        )

    # Flatten and sum the events and grams
    matching_events: Dict[str, List[db_models.IndexedEventGram]] = {}
    for query_result in all_gram_results:
        for matching_gram_result in query_result:
            referenced_event_id = matching_gram_result.event_ref.ref.id
            if referenced_event_id not in matching_events:
                matching_events[referenced_event_id] = [matching_gram_result]
            else:
                matching_events[referenced_event_id].append(matching_gram_result)

    compiled_events: List[EventMatch] = []
    for event_id, matching_grams in matching_events.items():
        matching_event = matching_grams[0].event_ref.get()
        compiled_events.append(
            EventMatch(
                event=matching_event,
                pure_relevance=sum([ieg.value for ieg in matching_grams]),
                datetime_weighted_relevance=sum(
                    [ieg.datetime_weighted_value for ieg in matching_grams]
                ),
                contained_grams=[ieg.unstemmed_gram for ieg in matching_grams],
                selected_context_span=max(
                    matching_grams, key=lambda ieg: ieg.value
                ).context_span,
                keywords=[
                    ieg.unstemmed_gram
                    for ieg in db_models.IndexedEventGram.collection.filter(
                        "event_ref",
                        "==",
                        matching_event.key,
                    )
                    .order("-value")
                    .fetch(5)
                ],
            )
        )

    # Sort compiled events by datetime weighted or pure relevance
    if sort_by == DATETIME_WEIGHTED_RELEVANCE.name:
        compiled_events = sorted(
            compiled_events,
            key=lambda e: e.datetime_weighted_relevance,
            reverse=True,
        )
    else:
        compiled_events = sorted(
            compiled_events,
            key=lambda e: e.pure_relevance,
            reverse=True,
        )

    # Log results
    for i, event_match in enumerate(compiled_events):
        print(
            f"Match {i}: {event_match.event.id} "
            f"(datetime: {event_match.event.event_datetime})"
        )
        print(
            f"Match pure tf-idf relevance: {event_match.pure_relevance}",
        )
        print(
            f"Match datetime weighted relevance: "
            f"{event_match.datetime_weighted_relevance}",
        )
        print(f"Match contained grams: {event_match.contained_grams}")
        print(f"Match keywords: {event_match.keywords}")
        print(f"Match context: {event_match.selected_context_span}")
        print("-" * 80)

        # Break out after first n
        if i + 1 == first:
            break

    log.info(f"Completed remote search in: {datetime.utcnow() - start_dt}")


def run_local_search(
    query: str,
    local_index: str,
    sort_by: str,
    first: int = 4,
) -> None:
    log.info("Running search against local index...")

    # Get stemmed grams
    stemmed_grams = get_stemmed_grams_from_query(query=query)

    # Begin timer
    start_dt = datetime.utcnow()

    # Read index
    try:
        index_df = dd.read_parquet(local_index, keep_default_na=False).compute()
    except IndexError:
        log.info("No local index found.")
        return

    # Check len df
    if len(index_df) == 0:
        log.info("No local index found.")
        return

    # For each stemmed gram find matching_events
    matching_events = index_df[index_df.stemmed_gram.isin(stemmed_grams)]

    # Group by event id, sum by tfidf, and sort
    summed_datetime_weighted_tfidf = (
        matching_events.groupby("event_id")
        .agg({DATETIME_WEIGHTED_RELEVANCE.local_field: sum})
        .reset_index()
    )
    summed_datetime_weighted_tfidf = summed_datetime_weighted_tfidf.rename(
        {
            DATETIME_WEIGHTED_RELEVANCE.local_field: (
                f"summed_{DATETIME_WEIGHTED_RELEVANCE.local_field}"
            )
        },
        axis=1,
    )
    summed_pure_tfidf = (
        matching_events.groupby("event_id")
        .agg({RELEVANCE.local_field: sum})
        .reset_index()
    )
    summed_pure_tfidf = summed_pure_tfidf.rename(
        {RELEVANCE.local_field: f"summed_{RELEVANCE.local_field}"}, axis=1
    )

    # Merge results with original
    matching_events = matching_events.merge(
        summed_datetime_weighted_tfidf,
        on="event_id",
        suffixes=("_stemmed_gram", "_summed"),
    )
    matching_events = matching_events.merge(
        summed_pure_tfidf,
        on="event_id",
        suffixes=("_stemmed_gram", "_summed"),
    )

    if sort_by == "datetime_weighted_relevance":
        matching_events = matching_events.sort_values(
            by=f"summed_{DATETIME_WEIGHTED_RELEVANCE.local_field}",
            ascending=False,
        )
    else:
        matching_events = matching_events.sort_values(
            by=f"summed_{RELEVANCE.local_field}",
            ascending=False,
        )

    # Group events and sort
    matching_events = matching_events.groupby("event_id", sort=False)

    # Report results
    print("Local index search results:")
    print("=" * 80)
    for i, group_details in enumerate(matching_events):
        # Unpack group details
        event_id, group = group_details

        # Get most important context span by contribution to sum
        most_important_context_span = (
            group[group[RELEVANCE.local_field] == group[RELEVANCE.local_field].max()]
            .iloc[0]
            .context_span
        )

        # Get keywords for event
        event_df = index_df[index_df.event_id == event_id].sort_values(
            "tfidf", ascending=False
        )
        match_keywords = list(event_df.unstemmed_gram)[:5]

        # Log results
        print(f"Match {i}: {event_id} (datetime: {group.iloc[0].event_datetime})")
        print(
            "Match pure tf-idf relevance: ",
            group.iloc[0][f"summed_{RELEVANCE.local_field}"],
        )
        print(
            "Match datetime weighted relevance: ",
            group.iloc[0][f"summed_{DATETIME_WEIGHTED_RELEVANCE.local_field}"],
        )
        print(f"Match contained grams: {list(group.unstemmed_gram)}")
        print(f"Match keywords: {match_keywords}")
        print(f"Match context: {most_important_context_span}")
        print("-" * 80)

        # Break out after first n
        if i + 1 == first:
            break

    log.info(f"Completed local search in: {datetime.utcnow() - start_dt}")


def main() -> None:
    try:
        args = Args()

        # Connect to the database
        fireo.connection(
            client=Client(
                project=args.instance,
                credentials=AnonymousCredentials(),
            )
        )

        run_remote_search(args.query, args.sort_by, args.first)
        run_local_search(args.query, args.local_index_glob, args.sort_by, args.first)
    except Exception as e:
        log.error("=============================================")
        log.error("\n\n" + traceback.format_exc())
        log.error("=============================================")
        log.error("\n\n" + str(e) + "\n")
        log.error("=============================================")
        sys.exit(1)


###############################################################################
# Allow caller to directly run this module (usually in development scenarios)

if __name__ == "__main__":
    main()
