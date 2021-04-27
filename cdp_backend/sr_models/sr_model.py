#!/usr/bin/env python
# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Union

from . import constants

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
        raw_transcript_save_path: Union[str, Path],
        timestamped_words_save_path: Optional[Union[str, Path]] = None,
        timestamped_sentences_save_path: Optional[Union[str, Path]] = None,
        timestamped_speaker_turns_save_path: Optional[Union[str, Path]] = None,
        phrases: Optional[List[str]] = None,
        **kwargs: Any
    ) -> SRModelOutputs:
        """
        Transcribe audio from file and store in text file.

        Parameters
        ----------
        file_uri: Union[str, Path]
            The uri to the audio file or caption file to transcribe.
        raw_transcript_save_path: Union[str, Path]
            Where the raw transcript should be saved to.
        timestamped_words_save_path: Optional[Union[str, Path]]
            If a timestamped words formatted transcript is produced, where it should be
            saved to.
        timestamped_sentences_save_path: Optional[Union[str, Path]]
            If a timestamped sentences formatted transcript is produced, where it
            should be saved to.
        timestamped_speaker_turns_save_path: Optional[Union[str, Path]]
            If a timestamped speaker turns formatted transcript is produced, where it
            should be saved to.

        Returns
        -------
        outputs: SRModelOutputs
            The outputs of the transcribe operation. Stores all available transcript
            paths as attributes as well as the overall confidence of the transciption
            accuracy.
        """

        return SRModelOutputs(
            Path(raw_transcript_save_path),
            1.0,
            Path(timestamped_words_save_path),  # type: ignore
            Path(timestamped_sentences_save_path),  # type: ignore
            Path(timestamped_speaker_turns_save_path),  # type: ignore
        )
