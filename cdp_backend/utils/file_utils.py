##!/usr/bin/env python

from __future__ import annotations

import logging
import math
import random
import re
import shutil
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import fireo
import fsspec
import requests
from fsspec.core import url_to_fs

from ..database import models as db_models

###############################################################################

log = logging.getLogger(__name__)

###############################################################################

MAX_THUMBNAIL_HEIGHT = 540
MAX_THUMBNAIL_WIDTH = 960


def with_stem(path: Path, stem: str) -> Path:
    """
    Create a path with a new stem.

    Parameters
    ----------
    path: Path
        The path to alter
    stem: str
        The string to be the new stem of the path

    Returns
    -------
    path: Path
        The new path with the replaced stem
    """
    return path.with_name(f"{stem}{path.suffix}")


def append_to_stem(path: Path, addition: str) -> Path:
    """
    Rename a file with a string appended to the path stem.

    Parameters
    ----------
    path: Path
        The path to alter
    addition: str
        The string to be appended to the path stem

    Returns
    -------
    path: Path
        The new path with the stem addition
    """
    return with_stem(path, f"{path.stem}{addition}")


def rename_with_stem(path: Path, stem: str) -> Path:
    """
    Rename a file with a string appended to the path stem.

    Parameters
    ----------
    path: Path
        The path to be renamed
    stem: str
        The string to become the new stem

    Returns
    -------
    path: Path
        The new path of the renamed file
    """
    return path.rename(with_stem(path, stem))


def rename_append_to_stem(path: Path, addition: str) -> Path:
    """
    Rename a file with a string appended to the path stem.

    Parameters
    ----------
    path: Path
        The path to be renamed
    addition: str
        The string to be appended to the path stem

    Returns
    -------
    path: Path
        The new path of the renamed file
    """
    return path.rename(append_to_stem(path, addition))


def get_media_type(uri: str) -> str | None:
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
    import dask.dataframe as dd

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


def resource_copy(  # noqa: C901
    uri: str,
    dst: str | Path | None = None,
    copy_suffix: bool = False,
    overwrite: bool = False,
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
    copy_suffix: bool
        Whether to copy the file suffix or not.
        Default: False (do not copy with suffix)
    overwrite: bool
        Boolean value indicating whether or not to overwrite a local resource with
        the same name if it already exists.

    Returns
    -------
    saved_path: str
        The path of where the resource ended up getting copied to.
    """
    uri_suffix = Path(uri.split("/")[-1].split("?")[0].split("#")[0]).suffix
    if dst is None:
        dst = uri.split("/")[-1]

    # Ensure dst doesn't exist
    dst = Path(dst).resolve()
    if dst.is_dir():
        if "v=" in str(uri):
            # Split by youtube video query parameter
            dst = dst / uri.split("v=")[-1]
        else:
            # Split by the last "/"
            dst = dst / uri.split("/")[-1]

    if copy_suffix:
        dst = dst.with_suffix(uri_suffix)

    # Ensure filename is less than 255 chars
    # Otherwise this can raise an OSError for too long of a filename
    if len(dst.name) > 255:
        dst = with_stem(dst, dst.stem[: (255 - len(dst.suffix))])

    # Ensure dest isn't a file
    if dst.is_file() and not overwrite:
        raise FileExistsError(dst)

    # Open requests connection to uri as a stream
    log.info(f"Beginning resource copy from: {uri}")
    # Get file system
    try:
        if uri.find("youtube.com") >= 0 or uri.find("youtu.be") >= 0:
            return youtube_copy(uri, dst, overwrite)

        if uri.find("vimeo.com") >= 0:
            return vimeo_copy(uri, dst, overwrite)

        if uri.endswith(".m3u8"):
            import m3u8_To_MP4

            # We add a uuid4 to the front of the filename because m3u8 files
            # are usually simply called playlist.m3u8 -- the result will be
            # f"{uuid}-{name}"
            mp4_name = dst.with_suffix(".mp4").name
            save_name = f"{uuid4()}-{mp4_name}"

            # Reset dst
            dst = dst.parent / save_name

            # Download and convert
            m3u8_To_MP4.download(
                uri,
                mp4_file_dir=dst.parent,
                mp4_file_name=save_name,
            )
            return str(dst)

        # Common case: http(s) URI
        if uri.startswith("http"):
            # The verify=False is passed to any http URIs
            # It was added because it's very common for SSL certs to be bad
            # See: https://github.com/CouncilDataProject/cdp-scrapers/pull/85
            # And: https://github.com/CouncilDataProject/seattle/runs/5957646032

            # Use stream=True to avoid downloading the entire file into memory
            # See: https://github.com/CouncilDataProject/cdp-backend/issues/235
            try:
                # This response must be closed after the copy is done. But using
                # `with requests.get() as response` fails mypy type checking.
                # See: https://requests.readthedocs.io/en/latest/user/advanced/#body-content-workflow
                response = requests.get(uri, stream=True, verify=False, timeout=1800)
                response.raise_for_status()
                with open(dst, "wb") as open_dst:
                    shutil.copyfileobj(
                        response.raw, open_dst, length=64 * 1024 * 1024  # 64MB chunks
                    )
            finally:
                response.close()

        else:
            # TODO: Add explicit use of GCS credentials until public read is fixed
            fs, remote_path = url_to_fs(uri)
            fs.get(remote_path, str(dst))
            log.info(f"Completed resource copy from: {uri}")
            log.info(f"Stored resource copy: {dst}")

        return str(dst)
    except Exception as e:
        log.error(
            f"Something went wrong during resource copy. "
            f"Attempted copy from: '{uri}', resulted in error."
        )
        raise e


def youtube_copy(uri: str, dst: Path, overwrite: bool = False) -> str:
    """
    Copy a video from YouTube to a local destination on the machine.

    Parameters
    ----------
    uri: str
        The url of the YouTube video to copy.
    dst: str
        The location of the file to download.
    overwrite: bool
        Boolean value indicating whether or not to overwrite a local video with
        the same name if it already exists.

    Returns
    -------
    dst: str
        The location of the downloaded file.
    """
    from yt_dlp import YoutubeDL

    dst = dst.with_suffix(".mp4")

    # Ensure dest isn't a file
    if dst.is_file() and not overwrite:
        raise FileExistsError(dst)

    ydl_opts = {"outtmpl": str(dst), "format": "mp4"}
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([uri])
        return str(dst)


def vimeo_copy(uri: str, dst: Path, overwrite: bool = False) -> str:
    """
    Copy a video from Vimeo to a local destination on the machine for analysis.

    Parameters
    ----------
    uri: str
        The url of the Vimeo video to copy.
    dst: str
        The location of the file to download.
    overwrite: bool
        Boolean value indicating whether or not to overwrite a local video with
        the same name if it already exists.

    Returns
    -------
    dst: str
        The location of the downloaded file.
    """
    from vimeo_downloader import Vimeo

    # Ensure dest isn't a file
    if dst.is_file() and not overwrite:
        raise FileExistsError(dst)

    # 9 is the length of the video id; no other
    # string of numbers in the URL has length 9 (thankfully)
    match = re.findall(r"\d{9}", uri)
    if len(match) == 0:
        raise ValueError(f"Could not extract video id from uri: '{uri}'")

    vid = match[0]
    v = Vimeo.from_video_id(video_id=vid)

    if len(v.streams) == 0:
        raise ValueError("File {} contains no downloadable streams", uri)
    best_stream = v.streams[-1]
    best_stream.download(download_directory=str(dst), filename=dst.name + ".mp4")
    return str(dst / f"{dst.name}.mp4")


def split_audio(
    video_read_path: str,
    audio_save_path: str,
    overwrite: bool = False,
) -> tuple[str, str, str]:
    """
    Split and store the audio from a video file using ffmpeg.

    Parameters
    ----------
    video_read_path: str
        Path to the video to split the audio from.
    audio_save_path: str
        Path to where the audio should be stored.
    overwrite: bool
        Whether to overwrite existing files or not.
        Default: False (do not overwrite)

    Returns
    -------
    resolved_audio_save_path: str
        Path to where the split audio file was saved.
    ffmpeg_stdout_path: str
        Path to the ffmpeg stdout log file.
    ffmpeg stderr path: str
        Path to the ffmpeg stderr log file.
    """
    import ffmpeg

    # Check paths
    resolved_video_read_path = Path(video_read_path).resolve(strict=True)
    resolved_audio_save_path = Path(audio_save_path).resolve()
    if resolved_audio_save_path.is_file() and not overwrite:
        raise FileExistsError(resolved_audio_save_path)
    if resolved_audio_save_path.is_dir():
        raise IsADirectoryError(resolved_audio_save_path)

    # Run dag
    log.debug(f"Beginning audio separation for: {video_read_path}")
    try:
        # Construct ffmpeg dag
        out, err = (
            ffmpeg.input(resolved_video_read_path)
            .output(
                filename=resolved_audio_save_path,
                format="wav",
                acodec="pcm_s16le",
                ac=1,
                ar="16k",
            )
            .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg._run.Error as e:
        log.error(e.stderr)
        raise e
    log.debug(f"Completed audio separation for: {video_read_path}")
    log.debug(f"Stored audio: {audio_save_path}")
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


def get_static_thumbnail(
    video_path: str, session_content_hash: str, seconds: int = 30
) -> str:
    """
    A function that produces a png thumbnail image from a video file.

    Parameters
    ----------
    video_path: str
        The URL of the video from which the thumbnail will be produced
    session_content_hash: str
        The video content hash. This will be used in the produced image file's name
    seconds: int
        Determines after how many seconds a frame will be selected to produce the
        thumbnail. The default is 30 seconds


    Returns
    -------
    str: cover_name
        The name of the thumbnail file:
        Always session_content_hash + "-static-thumbnail.png"
    """
    import imageio
    from PIL import Image

    reader = imageio.get_reader(video_path)
    png_path = ""
    if reader.get_length() > 1:
        png_path = f"{session_content_hash}-static-thumbnail.png"

    image = None
    try:
        frame_to_take = math.floor(reader.get_meta_data()["fps"] * seconds)
        image = reader.get_data(frame_to_take)
    except (ValueError, IndexError):
        reader = imageio.get_reader(video_path)
        image = reader.get_data(0)

    final_ratio = find_proper_resize_ratio(image.shape[0], image.shape[1])

    if final_ratio < 1:
        image = Image.fromarray(image).resize(
            (
                math.floor(image.shape[1] * final_ratio),
                math.floor(image.shape[0] * final_ratio),
            )
        )

    imageio.imwrite(png_path, image)

    return png_path


def get_hover_thumbnail(
    video_path: str,
    session_content_hash: str,
    num_frames: int = 10,
    duration: float = 6.0,
) -> str:
    """
    Produce a gif hover thumbnail from an mp4 video file.

    Parameters
    ----------
    video_path: str
        The URL of the video from which the thumbnail will be produced
    session_content_hash: str
        The video content hash. This will be used in the produced image file's name
    num_frames: int
        Determines the number of frames in the thumbnail
    duration: float
        Runtime of the produced GIF.
        Default: 6.0 seconds

    Returns
    -------
    str: cover_name
        The name of the thumbnail file:
        Always session_content_hash + "-hover-thumbnail.png"
    """
    import imageio
    import numpy as np
    from PIL import Image

    reader = imageio.get_reader(video_path)
    gif_path = ""
    if reader.get_length() > 1:
        gif_path = f"{session_content_hash}-hover-thumbnail.gif"

    # Get first frame
    sample = reader.get_data(0)
    height = sample.shape[0]
    width = sample.shape[1]
    final_ratio = find_proper_resize_ratio(height, width)

    with imageio.get_writer(gif_path, mode="I", duration=duration * 1000) as writer:
        selected_frames = 0
        for frame in reader:
            # 1% chance to use the frame
            if random.random() > 0.99:
                image = Image.fromarray(frame)
                if final_ratio < 1:
                    image = image.resize(
                        (
                            math.floor(width * final_ratio),
                            math.floor(height * final_ratio),
                        )
                    )

                final_image = np.asarray(image).astype(np.uint8)
                writer.append_data(final_image)
                selected_frames += 1

            if selected_frames >= num_frames:
                break

    return gif_path


def find_proper_resize_ratio(height: int, width: int) -> float:
    """
    Return the proper ratio to resize a thumbnail greater than 960 x 540 pixels.

    Parameters
    ----------
    height: int
        The height, in pixels, of the thumbnail to be resized.
    width: int
        The width, in pixels, of the thumbnail to be resized.

    Returns
    -------
    final_ratio: float
        The ratio by which the thumbnail will be resized.
        If the ratio is less than 1, the thumbnail is too large and should be resized
        by a factor of final_ratio.
        If the ratio is greater than or equal to 1, the thumbnail is not too large and
        should not be resized.
    """
    if height > MAX_THUMBNAIL_HEIGHT or width > MAX_THUMBNAIL_WIDTH:
        height_ratio = MAX_THUMBNAIL_HEIGHT / height
        width_ratio = MAX_THUMBNAIL_WIDTH / width

        if height_ratio > width_ratio:
            final_ratio = height_ratio
        else:
            final_ratio = width_ratio

        return final_ratio

    return 2


def hash_file_contents(uri: str, buffer_size: int = 2**16) -> str:
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


def convert_video_to_mp4(
    video_filepath: Path,
    start_time: str | None,
    end_time: str | None,
    output_path: Path = None,
) -> Path:
    """
    Converts a video to an equivalent MP4 file.

    Parameters
    ----------
    video_filepath: str
        The filepath of the video to convert.
    start_time: str
        The start time to trim the video in HH:MM:SS.
    end_time: str
        The end time to trim the video in HH:MM:SS.
    output_path: Path
        The output path to place the clip at.

    Returns
    -------
    output_path: str
        The filepath of the converted MP4 video.
    """
    output_path = output_path or video_filepath.with_suffix(".mp4")
    output_path = clip_and_reformat_video(
        video_filepath=video_filepath,
        start_time=start_time,
        end_time=end_time,
        output_path=output_path,
        output_format="mp4",
    )
    log.info("Finished converting {} to mp4".format(video_filepath))

    return output_path


def generate_file_storage_name(file_uri: str, suffix: str) -> str:
    """
    Generate a filename using the hash of the file contents and some provided suffix.

    Parameters
    ----------
    file_uri: str
        The URI to the file to hash.
    suffix: str
        The suffix to append to the hash as a part of the filename.

    Returns
    -------
    dst: str
        The name of the file as it should be on Google Cloud Storage.
    """
    hash_str = hash_file_contents(file_uri)
    return f"{hash_str}-{suffix}"


def download_video_from_session_id(
    credentials_file: str,
    session_id: str,
    dest: str | Path | None = None,
) -> str | Path:
    """
    Using the session_id provided, pulls the associated
    video, and places it the destination.

    Parameters
    ----------
    credentials_file: str
        The path to the Google Service Account credentials JSON file used
        to initialize the file store connection.
    session_id: str
        The id of the session to retrive the video for.
    dest: Optional[Union[str, Path]]
        A destination to store the file to.
        This is passed directly to the resource_copy function.

    Returns
    -------
    Path
        The destination path.

    See Also
    --------
    cdp_backend.utils.file_utils.resource_copy
        The function that downloads the video from remote host.
    """
    # Connect to the database
    fireo.connection(from_file=credentials_file)

    # Fetch session
    session = db_models.Session.collection.get(session_id)

    # Download
    return resource_copy(session.video_uri, dest)


def clip_and_reformat_video(
    video_filepath: Path,
    start_time: str | None,
    end_time: str | None,
    output_path: Path = None,
    output_format: str = "mp4",
) -> Path:
    """
    Clip a video file to a specific time range and convert to requested output format.

    Parameters
    ----------
    video_filepath: Path
        The filepath of the video to clip.
    start_time: str
        The start time of the clip in HH:MM:SS.
    end_time: str
        The end time of the clip in HH:MM:SS.
    output_path: Path
        The output path to place the clip at.
    output_format: str
        The output format.
        Default: "mp4"

    Returns
    -------
    Path:
        The path where the new file was stored to.
    """
    import ffmpeg

    output_path = output_path or append_to_stem(video_filepath, "_clipped")

    output_kwargs = {"format": output_format}
    if should_copy_video(video_filepath, output_format):
        log.info(
            f"Video {video_filepath} is already h264, "
            "it will be clipped and copied instead of clipped and re-encoded."
        )
        output_kwargs["codec"] = "copy"

    try:
        ffmpeg_stdout, ffmpeg_stderr = (
            ffmpeg.input(
                video_filepath,
                ss=start_time or "0",
                to=end_time or "99:59:59",
            )
            .output(
                filename=str(output_path),
                **output_kwargs,
            )
            .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg._run.Error as e:
        log.error(e.stderr)
        raise e

    log.info(f"Finished clipping {video_filepath} to {output_path}")
    log.debug(ffmpeg_stdout)
    if ffmpeg_stderr:
        log.error(ffmpeg_stderr)

    return output_path


def should_copy_video(video_filepath: Path, output_format: str = "mp4") -> bool:
    """
    Check if the video should be copied using ffmpeg StreamCopy codec or if it should
    be re-encoded as h264.

    A video will be copied iff the following conditions are met:
    - The video at video_filepath has a .mp4 extension
    - The desired output format is mp4
    - The video at video_filepath has a video stream with a codec of h264

    Parameters
    ----------
    video_filepath: Path
        The filepath of the video under scrutiny.
    output_format: str
        The desired output format of the video at video_filepath.

    Returns
    -------
    bool:
        True if the video should be copied, False if it should be re-encoded.
    """
    if video_filepath.suffix.lower() != ".mp4":
        return False

    if output_format.lower() != "mp4":
        return False

    import ffmpeg

    try:
        streams = ffmpeg.probe(video_filepath)["streams"]
    except ffmpeg.Error as e:
        log.warning(
            f"Failed to probe {video_filepath}. "
            "Unable to determine if video should be copied or re-encoded."
            f"Falling back to re-encoding. ffmpeg error: {e.stderr}"
        )
        return False

    should_copy_video = False
    for stream in streams:
        if stream["codec_type"] == "video" and stream["codec_name"] == "h264":
            should_copy_video = True
            break

    return should_copy_video
