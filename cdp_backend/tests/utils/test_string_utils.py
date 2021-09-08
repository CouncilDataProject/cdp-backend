#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest

from cdp_backend.utils import string_utils

#############################################################################


@pytest.mark.parametrize(
    "text, expected, clean_stop_words",
    [
        ("hello and goodbye", "hello goodbye", True),
        ("   \t\n   hello and to of a         goodbye         ", "hello goodbye", True),
        ("hell'o    and   good-bye", "hello goodbye", True),
        ("and", "", True),
        ("hello and goodbye", "hello and goodbye", False),
        (
            "   \t\n   hello and to of a         goodbye         ",
            "hello and to of a goodbye",
            False,
        ),
        ("hell'o    and   good-bye", "hello and goodbye", False),
        ("and", "and", False),
    ],
)
def test_clean_text(text: str, expected: str, clean_stop_words: bool) -> None:
    assert string_utils.clean_text(text, clean_stop_words=clean_stop_words) == expected


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
