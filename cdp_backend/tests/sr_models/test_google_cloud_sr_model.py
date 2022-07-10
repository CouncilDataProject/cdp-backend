#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
import re
from pathlib import Path
from typing import Any, List, Type
from unittest import mock

import pytest
from google.cloud import speech_v1p1beta1 as speech

from cdp_backend.sr_models.google_cloud_sr_model import (
    GOOGLE_SPEECH_ADAPTION_CLASSES,
    GoogleCloudSRModel,
)

expected_sentence_1 = "Hello everyone, and thank you for coming."
expected_sentence_2 = "Will the clerk begin by taking roll."


@pytest.fixture
def example_audio(resources_dir: Path) -> Path:
    return resources_dir / "example_audio.wav"


@pytest.fixture
def fake_creds_path(resources_dir: Path) -> Path:
    return resources_dir / "fake_creds.json"


class FakeRecognizeTime:
    def __init__(self, seconds: float):
        self.seconds = seconds
        self.microseconds = 0


class FakeRecognizeWord:
    def __init__(self, word: str, start_time: float, end_time: float):
        self.word = word
        self.start_time = FakeRecognizeTime(start_time)
        self.end_time = FakeRecognizeTime(end_time)


class FakeRecognizeAlternative:
    def __init__(self, transcript: str, words: List[FakeRecognizeWord]):
        self.words = words
        self.transcript = transcript
        self.confidence = random.random()


class FakeRecognizeResult:
    def __init__(self, alternatives: List[FakeRecognizeAlternative]):
        self.alternatives = alternatives


class FakeRecognizeResults:
    results = [
        FakeRecognizeResult(
            [
                FakeRecognizeAlternative(
                    "Hello everyone, and thank you for coming.",
                    [
                        FakeRecognizeWord("Hello", 0.0, 0.6),
                        FakeRecognizeWord("everyone,", 0.7, 1.1),
                        FakeRecognizeWord("and", 1.2, 1.4),
                        FakeRecognizeWord("thank", 1.5, 1.7),
                        FakeRecognizeWord("you", 1.8, 1.9),
                        FakeRecognizeWord("for", 2.0, 2.1),
                        FakeRecognizeWord("coming.", 2.2, 2.4),
                    ],
                )
            ]
        ),
        FakeRecognizeResult(
            [
                FakeRecognizeAlternative(
                    "Will the clerk begin by taking roll.",
                    [
                        FakeRecognizeWord("Will", 3.0, 3.1),
                        FakeRecognizeWord("the", 3.2, 3.3),
                        FakeRecognizeWord("clerk", 3.4, 3.5),
                        FakeRecognizeWord("begin", 3.6, 3.7),
                        FakeRecognizeWord("by", 3.8, 3.9),
                        FakeRecognizeWord("taking", 4.0, 4.1),
                        FakeRecognizeWord("roll.", 4.2, 4.3),
                    ],
                )
            ]
        ),
    ]


class FakeRecognizeOperation:
    def __init__(self) -> None:
        self._result = FakeRecognizeResults

    def result(self, **kwargs: Any) -> Type[FakeRecognizeResults]:
        return self._result


def test_google_cloud_sr_model_init(fake_creds_path: str) -> None:
    GoogleCloudSRModel(fake_creds_path)


@pytest.mark.parametrize(
    "phrases, cleaned",
    [
        (None, []),
        ([], []),
        (
            [str(i) for i in range(600)],
            [str(i) for i in range(500 - len(GOOGLE_SPEECH_ADAPTION_CLASSES.phrases))],
        ),
        (
            [
                "this will be chunked to less than one hundred characters because that "
                "is the maximum allowed by google cloud speech recognition"
            ],
            [
                "this will be chunked to less than one hundred characters because that "
                "is the maximum allowed by"
            ],
        ),
        (["-" * 100] * 200, ["-" * 100] * 100),
    ],
)
def test_clean_phrases(phrases: List[str], cleaned: List[str]) -> None:
    assert GoogleCloudSRModel._clean_phrases(phrases) == cleaned


def has_only_non_deliminating_chars(word: str) -> bool:
    return not re.search(r"[^a-zA-Z0-9'\-]", word)


def test_google_cloud_transcribe(fake_creds_path: str, example_audio: str) -> None:
    with mock.patch(
        "google.cloud.speech_v1p1beta1.SpeechClient.from_service_account_file"
    ) as mocked_client_init:
        mocked_client = mock.Mock(spec=speech.SpeechClient)
        mocked_client.long_running_recognize.return_value = FakeRecognizeOperation()
        mocked_client_init.return_value = mocked_client

        sr_model = GoogleCloudSRModel(fake_creds_path)

        transcript = sr_model.transcribe(str(example_audio))

        assert expected_sentence_1 == transcript.sentences[0].text
        assert expected_sentence_2 == transcript.sentences[1].text
        assert transcript.sentences[0].index == 0
        assert transcript.sentences[1].index == 1

        for sentence in transcript.sentences:
            for word in sentence.words:
                assert has_only_non_deliminating_chars(word.text) is True
