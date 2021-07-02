#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import shutil
from hashlib import sha256
from pathlib import Path
from typing import List, Optional, Tuple, Union

import dask.dataframe as dd
import ffmpeg
import fsspec
from prefect import task

###############################################################################

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)4s: %(module)s:%(lineno)4s %(asctime)s] %(message)s",
)
log = logging.getLogger(__name__)

###############################################################################


def get_media_type(uri: str) -> Optional[str]:
    """
    Get the IANA media type for the provided URI.
    If one could not be found, return None.

    Parameters
    ----------
    uri: str
        The URI to get the IANA media type for.

    Returns
    -------
    mtype: Optional[str]:
        The found matching IANA media type.
    """
    # Media types retrieved from:
    # http://www.iana.org/assignments/media-types/media-types.xhtml
    media_types = dd.read_csv(
        str(Path(__file__).parent / "resources" / "content-types-*.csv")
    )

    # Get suffix from URI
    splits = uri.split(".")
    suffix = splits[-1]

    # Find content type
    matching = media_types[media_types["Name"] == suffix].compute()

    # If there is exactly one matching type, return it
    if len(matching) == 1:
        return matching["Template"].values[0]

    # Otherwise, return none
    return None


def resource_copy(
    uri: str, dst: Optional[Union[str, Path]] = None, overwrite: bool = False
) -> str:
    """
    Copy a resource (local or remote) to a local destination on the machine.

    Parameters
    ----------
    uri: str
        The uri for the resource to copy.
    dst: Optional[Union[str, Path]]
        A specific destination to where the copy should be placed. If None provided
        stores the resource in the current working directory.
    overwrite: bool
        Boolean value indicating whether or not to overwrite a local resource with
        the same name if it already exists.

    Returns
    -------
    saved_path: str
        The path of where the resource ended up getting copied to.
    """
    if dst is None:
        dst = uri.split("/")[-1]

    # Ensure dst doesn't exist
    dst = Path(dst).resolve()
    if dst.is_dir():
        dst = dst / uri.split("/")[-1]
    if dst.is_file() and not overwrite:
        raise FileExistsError(dst)

    # Open requests connection to uri as a stream
    log.debug(f"Beginning external resource copy from: {uri}")
    with fsspec.open(uri, "rb") as open_source:
        with open(dst, "wb") as open_target:
            shutil.copyfileobj(open_source, open_target)
    log.debug(f"Completed external resource copy from: {uri}")
    log.info(f"Stored external resource copy: {dst}")

    return str(dst)


def split_audio(
    video_read_path: str,
    audio_save_path: str,
    overwrite: bool = False,
) -> Tuple[str, str, str]:
    """
    Split and store the audio from a video file using ffmpeg.

    Parameters
    ----------
    video_read_path: str
        Path to the video to split the audio from.
    audio_save_path: str
        Path to where the audio should be stored.

    Returns
    -------
    resolved_audio_save_path: str
        Path to where the split audio file was saved.
    ffmpeg_stdout_path: str
        Path to the ffmpeg stdout log file.
    ffmpeg stderr path: str
        Path to the ffmpeg stderr log file.
    """

    # Check paths
    resolved_video_read_path = Path(video_read_path).resolve(strict=True)
    resolved_audio_save_path = Path(audio_save_path).resolve()
    if resolved_audio_save_path.is_file() and not overwrite:
        raise FileExistsError(resolved_audio_save_path)
    if resolved_audio_save_path.is_dir():
        raise IsADirectoryError(resolved_audio_save_path)

    # Construct ffmpeg dag
    stream = ffmpeg.input(resolved_video_read_path)
    stream = ffmpeg.output(
        stream,
        filename=resolved_audio_save_path,
        format="wav",
        acodec="pcm_s16le",
        ac=1,
        ar="16k",
    )

    # Run dag
    log.debug(f"Beginning audio separation for: {video_read_path}")
    out, err = ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
    log.debug(f"Completed audio separation for: {video_read_path}")
    log.info(f"Stored audio: {audio_save_path}")

    # Store logs
    ffmpeg_stdout_path = resolved_audio_save_path.with_suffix(".out")
    ffmpeg_stderr_path = resolved_audio_save_path.with_suffix(".err")

    with open(ffmpeg_stdout_path, "wb") as write_out:
        write_out.write(out)
    with open(ffmpeg_stderr_path, "wb") as write_err:
        write_err.write(err)

    return (
        str(resolved_audio_save_path),
        str(ffmpeg_stdout_path),
        str(ffmpeg_stderr_path),
    )


def hash_file_contents_task(uri: str, buffer_size: int = 2 ** 16) -> str:
    """
    Return the SHA256 hash of a file's content.

    Parameters
    ----------
    uri: str
        The uri for the file to hash.
    buffer_size: int
        The number of bytes to read at a time.
        Default: 2^16 (64KB)

    Returns
    -------
    hash: str
        The SHA256 hash for the file contents.
    """
    hasher = sha256()

    with fsspec.open(uri, "rb") as open_resource:
        while True:
            block = open_resource.read(buffer_size)
            if not block:
                break

            hasher.update(block)

    return hasher.hexdigest()


def join_strs_and_extension(
    parts: List[str], extension: str, delimiter: str = "_"
) -> str:
    name_without_suffix = delimiter.join(parts)
    return f"{name_without_suffix}.{extension}"
