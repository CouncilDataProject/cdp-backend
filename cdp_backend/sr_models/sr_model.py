#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Union

from ..pipeline import transcript_model

###############################################################################


class SRModel(ABC):
    @abstractmethod
    def transcribe(
        self, file_uri: Union[str, Path], **kwargs: Any
    ) -> transcript_model.Transcript:
        """
        Transcribe audio from file and return a Transcript model.

        Parameters
        ----------
        file_uri: Union[str, Path]
            The uri to the audio file or caption file to transcribe.

        Returns
        -------
        outputs: transcript_model.Transcript
            The transcript model for the supplied media file.
        """

    @staticmethod
    def _clean_word(word: str) -> str:
        cleaned_word = re.sub(r"[^\w\/\-\']+", "", word).lower()

        return cleaned_word
