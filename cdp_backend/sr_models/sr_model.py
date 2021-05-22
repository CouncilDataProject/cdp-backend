#!/usr/bin/env python
# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Union

from ..pipeline.transcript_model import Transcript

###############################################################################


class SRModelOutputs(NamedTuple):
    raw_path: Path
    confidence: float
    timestamped_words_path: Optional[Path] = None
    timestamped_sentences_path: Optional[Path] = None
    timestamped_speaker_turns_path: Optional[Path] = None
    extras: Optional[Dict[str, Any]] = None


class SRModel(ABC):
    @abstractmethod
    def transcribe(
        self,
        file_uri: Union[str, Path],
        phrases: Optional[List[str]] = None,
        **kwargs: Any
    ) -> Transcript:
        """
        Transcribe audio from file and store in text file.

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
