#!/usr/bin/env python
# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union

###############################################################################


class AudioSplitter(ABC):
    """
    Why is this not just a single function?

    Making it available to the backend maintainers to pass arguments to the instance of
    the class and retain state may be useful. An example that I can think of: Instead
    of splitting the entire video into a single audio clip, a parameter could be passed
    to the instance that splits the audio into smaller portions and needs to track
    additional metadata.
    """

    @abstractmethod
    def split(
        self, video_read_path: Union[str, Path], audio_save_path: Union[str, Path]
    ) -> Path:
        """
        Split and store the audio from a video file.

        Parameters
        ----------
        video_read_path: Union[str, Path]
            Path to the video to split the audio from.
        audio_save_path: Union[str, Path]
            Path to where the audio should be stored.

        Returns
        -------
        audio_save_path: Path
            Path to where the split audio was saved.
        """

        return Path("/root/.local/path/to/file/id.wav")
