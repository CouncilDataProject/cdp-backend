#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
from unittest import mock
from typing import Any, List, Type
from py._path.local import LocalPath
from pathlib import Path


import pytest
from google.cloud import speech_v1p1beta1 as speech

from cdp_backend.sr_models.google_cloud_sr_model import GoogleCloudSRModel


@pytest.fixture
def example_audio(data_dir: Path) -> Path:
    return data_dir / "example_audio.wav"


@pytest.fixture
def fake_creds_path(data_dir: Path) -> Path:
    return data_dir / "fake_creds.json"


class FakeRecognizeTime:
    def __init__(self, seconds: float):
        self.seconds = seconds
        self.nanos = 0


class FakeRecognizeWord:
    def __init__(self, word: str, start_time: float, end_time: float):
        self.word = word
        self.start_time = FakeRecognizeTime(start_time)
        self.end_time = FakeRecognizeTime(end_time)


class FakeRecognizeAlternative:
    def __init__(self, words: List[FakeRecognizeWord]):
        self.words = words
        self.confidence = random.random()


class FakeRecognizeResult:
    def __init__(self, alternatives: List[FakeRecognizeAlternative]):
        self.alternatives = alternatives


class FakeRecognizeResults:
    results = [
        FakeRecognizeResult(
            [
                FakeRecognizeAlternative(
                    [
                        FakeRecognizeWord("Hello", 0.0, 0.6),
                        FakeRecognizeWord("everyone", 0.7, 1.1),
                        FakeRecognizeWord("and", 1.2, 1.4),
                        FakeRecognizeWord("thank", 1.5, 1.7),
                        FakeRecognizeWord("you", 1.8, 1.9),
                        FakeRecognizeWord("for", 2.0, 2.1),
                        FakeRecognizeWord("coming.", 2.2, 2.4),
                    ]
                )
            ]
        ),
        FakeRecognizeResult(
            [
                FakeRecognizeAlternative(
                    [
                        FakeRecognizeWord("Will", 3.0, 3.1),
                        FakeRecognizeWord("the", 3.2, 3.3),
                        FakeRecognizeWord("clerk", 3.4, 3.5),
                        FakeRecognizeWord("begin", 3.6, 3.7),
                        FakeRecognizeWord("by", 3.8, 3.9),
                        FakeRecognizeWord("taking", 4.0, 4.1),
                        FakeRecognizeWord("roll.", 4.2, 4.3),
                    ]
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
        ([str(i) for i in range(600)], [str(i) for i in range(500)]),
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


def test_google_cloud_transcribe(fake_creds_path: str, example_audio: str, tmpdir: LocalPath) -> None:
    with mock.patch(
        "google.cloud.speech_v1p1beta1.SpeechClient.from_service_account_json"
    ) as mocked_client_init:
        mocked_client = mock.Mock(spec=speech.SpeechClient)
        mocked_client.long_running_recognize.return_value = FakeRecognizeOperation()
        mocked_client_init.return_value = mocked_client

        sr_model = GoogleCloudSRModel(fake_creds_path)

        sr_model.transcribe(
            str(example_audio),
            tmpdir / "raw.json",
            tmpdir / "words.json",
            tmpdir / "sentences.json",
        )
