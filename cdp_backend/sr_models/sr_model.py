#!/usr/bin/env python
# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List, Optional, Union

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
