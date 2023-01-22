#!/usr/bin/env python

import pytest

from cdp_backend.utils import string_utils


#############################################################################


@pytest.mark.parametrize(
    "text, expected, clean_stop_words, clean_emojis",
    [
        (
            "hello and goodbye",
            "hello goodbye",
            True,
            True,
        ),
        (
            "   \t\n   hello and to of a         goodbye         ",
            "hello goodbye",
            True,
            True,
        ),
        (
            "hell'o    and   good-bye",
            "hello goodbye",
            True,
            True,
        ),
        (
            "and",
            "",
            True,
            True,
        ),
        (
            "hello and goodbye",
            "hello and goodbye",
            False,
            True,
        ),
        (
            "   \t\n   hello and to of a         goodbye         ",
            "hello and to of a goodbye",
            False,
            True,
        ),
        (
            "hell'o    and   good-bye",
            "hello and goodbye",
            False,
            True,
        ),
        (
            "and",
            "and",
            False,
            True,
        ),
        (
            "♪ Seattle channel music ♪",
            "Seattle channel music",
            False,
            True,
        ),
        (
            "\t\n    \t♪ Seattle channel music ♪",
            "Seattle channel music",
            False,
            True,
        ),
    ],
)
def test_clean_text(
    text: str,
    expected: str,
    clean_stop_words: bool,
    clean_emojis: bool,
) -> None:
    assert (
        string_utils.clean_text(
            text,
            clean_stop_words=clean_stop_words,
            clean_emojis=clean_emojis,
        )
        == expected
    )


@pytest.mark.parametrize(
    "text, expected",
    [
        (
            "https://storage.googleapis.com/download/storage/v1/b/"
            + "bucket.appspot.com/o/wombo_combo.mp4?alt=media",
            "gs://bucket.appspot.com/wombo_combo.mp4",
        ),
        # Invalid format
        (
            "https://storage.googleapis.com/download/storage/"
            + "bucket.appspot.com/o/wombo_combo.mp4?alt=media",
            "",
        ),
    ],
)
def test_convert_gcs_json_url_to_gsutil_form(text: str, expected: str) -> None:
    assert string_utils.convert_gcs_json_url_to_gsutil_form(text) == expected
