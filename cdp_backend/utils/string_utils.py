##!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
import string

###############################################################################

log = logging.getLogger(__name__)

###############################################################################


def clean_text(text: str, clean_stop_words: bool = False) -> str:
    """
    Clean text of common characters and extra formatting.

    Parameters
    ----------
    text: str
        The raw text to clean.
    clean_stop_words: bool
        Should English stop words be removed from the raw text or not.
        Default: False (do not remove stop words)

    Returns
    -------
    cleaned_text: str
        The cleaned text.
    """
    # Remove new line and tab characters
    cleaned_formatting = text.replace("\n", " ").replace("\t", " ")

    # Replace common sentence structures
    cleaned_sentence_structs = cleaned_formatting.replace("--", " ")

    # Remove punctuation except periods
    cleaned_punctuation = re.sub(
        f"[{re.escape(string.punctuation)}]", "", cleaned_sentence_structs
    )

    # Remove stopwords
    if clean_stop_words:
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

        joined_stopwords = "|".join(STOPWORDS)
        cleaned_stopwords = re.sub(
            r"\b(" + joined_stopwords + r")\b",
            "",
            cleaned_punctuation,
        )
    else:
        # Update for mypy typing
        cleaned_stopwords = cleaned_punctuation

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


def convert_gcs_json_url_to_gsutil_form(url: str) -> str:
    """
    Convert a GCS JSON API url to its corresponding gsutil uri.

    Parameters
    ----------
    url: str
        The url in GCS JSON API form.

    Returns
    -------
    gsutil_url: str
        The url in gsutil form. Returns empty string if the input url doesn't
        match the form.
    """

    found_bucket, found_filename = None, None

    bucket = re.search("storage.googleapis.com/download/storage/v1/b/(.+?)/o", url)
    if bucket:
        found_bucket = str(bucket.group(1))

    filename = re.search(r"/o/(.+?)\?alt=media", url)
    if filename:
        found_filename = str(filename.group(1))

    if found_bucket and found_filename:
        return f"gs://{found_bucket}/{found_filename}"

    return ""
