#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import traceback

import dask.dataframe as dd
from nltk import ngrams
from nltk.stem import SnowballStemmer

from cdp_backend.pipeline.event_index_pipeline import clean_text

###############################################################################

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)4s: %(module)s:%(lineno)4s %(asctime)s] %(message)s",
)
log = logging.getLogger(__name__)

###############################################################################


class Args(argparse.Namespace):
    def __init__(self):
        self.__parse()

    def __parse(self):
        p = argparse.ArgumentParser(
            prog="search_cdp_events", description="Search CDP events given a query."
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
            default="datetime_weighted_relevance",
            choices=["datetime_weighted_relevance", "relevance"],
            help="Choice between datetime weighted and pure relevance (TFIDF score).",
        )
        p.add_argument(
            "-f",
            "--first",
            type=int,
            default=5,
            help="Number of results to return.",
        )
        p.add_argument(
            "-l",
            "--local_index",
            type=str,
            default="tfidf-*.parquet",
            help="The file glob for which files to use for reading a planned index.",
        )
        p.parse_args(namespace=self)


###############################################################################


def run_local_search(query: str, local_index: str, sort_by: str, first: int = 10):
    log.info("Running search against local index...")

    # Spawn stemmer
    stemmer = SnowballStemmer("english")

    # Create stemmed grams for query
    query = clean_text(query).split()
    stemmed_grams = []
    for n_gram_size in range(1, 3):
        grams = ngrams(query, n_gram_size)
        for gram in grams:
            stemmed_grams.append(" ".join(stemmer.stem(term.lower()) for term in gram))

    # Read index
    index_df = dd.read_parquet(local_index, keep_default_na=False).compute()

    # For each stemmed gram find matching_events
    matching_events = index_df[index_df.stemmed_gram.isin(stemmed_grams)]

    # Group by event id, sum by tfidf, and sort
    summed_datetime_weighted_tfidf = (
        matching_events.groupby("event_id")
        .agg({"datetime_weighted_tfidf": sum})
        .reset_index()
    )
    summed_datetime_weighted_tfidf = summed_datetime_weighted_tfidf.rename(
        {"datetime_weighted_tfidf": "summed_datetime_weighted_tfidf"}, axis=1
    )
    summed_pure_tfidf = (
        matching_events.groupby("event_id").agg({"tfidf": sum}).reset_index()
    )
    summed_pure_tfidf = summed_pure_tfidf.rename({"tfidf": "summed_tfidf"}, axis=1)

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
            by="summed_datetime_weighted_tfidf",
            ascending=False,
        )
    else:
        matching_events = matching_events.sort_values(
            by="summed_tfidf",
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
            group[group.tfidf == group.tfidf.max()].iloc[0].context_span
        )

        # Get keywords for event
        event_df = index_df[index_df.event_id == event_id].sort_values(
            "tfidf", ascending=False
        )
        match_keywords = list(event_df.unstemmed_gram)[:5]

        # Log results
        print(f"Match {i}: {event_id} (datetime: {group.iloc[0].event_datetime})")
        print(f"Match pure tf-idf relevance: {group.iloc[0].summed_tfidf}")
        print(
            f"Match datetime weighted relevance: "
            f"{group.iloc[0].summed_datetime_weighted_tfidf}"
        )
        print(f"Match contained grams: {list(group.unstemmed_gram)}")
        print(f"Match keywords: {match_keywords}")
        print(f"Match context: {most_important_context_span}")
        print("-" * 80)

        # Break out after first n
        if i + 1 == first:
            break


def main() -> None:
    try:
        args = Args()
        run_local_search(args.query, args.local_index, args.sort_by, args.first)
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
