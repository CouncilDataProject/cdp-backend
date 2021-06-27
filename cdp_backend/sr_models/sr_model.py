#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Union

from ..pipeline.transcript_model import Transcript

###############################################################################


class SRModel(ABC):
    @abstractmethod
    def transcribe(self, file_uri: Union[str, Path], **kwargs: Any) -> Transcript:
        """
        Transcribe audio from file and return a Transcript model.

        Parameters
        ----------
        file_uri: Union[str, Path]
            The uri to the audio file or caption file to transcribe.

        Returns
        -------
        outputs: Transcript
            The transcript model for the supplied media file.
        """

        return Transcript(0.0, "", "", "", [])

    @staticmethod
    def _clean_word(word: str) -> str:
        text_cleaner = re.compile(r"[^a-zA-Z0-9'\-]")
        cleaned_word = text_cleaner.sub("", word).lower()

        return cleaned_word
