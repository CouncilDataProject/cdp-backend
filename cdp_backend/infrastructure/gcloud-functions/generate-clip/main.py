#!/usr/bin/env python
# -*- coding: utf-8 -*-f

import logging
from pathlib import Path
from typing import Dict, NoReturn, Union
from uuid import uuid4

import functions_framework
from flask import Request, abort, escape
from werkzeug.datastructures import MultiDict

from cdp_backend.file_store.functions import upload_file_and_return_link
from cdp_backend.utils.file_utils import (
    clip_and_reformat_video,
    download_video_from_session_id,
)

###############################################################################

CLIP_STORAGE = "GENERATED_CLIPS"
CREDENTIALS_PATH = "GOOGLE_CREDENTIALS.json"

###############################################################################


def _unpack_param(
    request_json: Dict[str, str],
    request_args: MultiDict[str, str],
    param: str,
) -> Union[str, NoReturn]:
    if request_json and param in request_json:
        return request_json[param]
    if request_args and param in request_args:
        return request_args[param]

    # Bad request
    logging.error(f"No parameter with name: '{param}'")
    return abort(400)


def _hhmmss_as_seconds(time_str: str) -> Union[int, NoReturn]:
    try:
        hours, minutes, seconds = time_str.split(":")
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds)
    except Exception:
        # Bad request
        logging.error(f"Something went wrong while splitting to seconds: {time_str}")
        return abort(400)


@functions_framework.http
def generate_clip(request: Request) -> Union[str, NoReturn]:
    """HTTP Cloud Function.
    Args:
        request (flask.Request): The request object.
        <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>
    Returns:
        The link to the process audio/video clip.
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """
    # Get args
    request_json = request.get_json(silent=True)
    request_args = request.args

    # See exception / abort handling here:
    # https://cloud.google.com/functions/docs/monitoring/error-reporting
    # https://cloud.google.com/endpoints/docs/frameworks/java/exceptions

    # Unpack the params
    start_time = _unpack_param(request_json, request_args, "start")
    end_time = _unpack_param(request_json, request_args, "end")
    session_id = _unpack_param(request_json, request_args, "sessionId")
    output_format = _unpack_param(request_json, request_args, "format")
    project_id = _unpack_param(request_json, request_args, "projectId")

    # Check that user isn't asking for longer than 5 minutes
    start_seconds = _hhmmss_as_seconds(start_time)
    end_seconds = _hhmmss_as_seconds(end_time)
    clip_duration = end_seconds - start_seconds
    if clip_duration > (5 * 60):
        logging.error("Requested clip duration exceeds allowed maximum.")
        return abort(400)

    # Download the session video
    try:
        local_video = download_video_from_session_id(
            credentials_file=CREDENTIALS_PATH,
            session_id=session_id,
            dest="/tmp/full-video",
        )
    except Exception as e:
        logging.error(
            f"Failed to download video from session id '{session_id}'. Exception: {e}",
        )
        return abort(400)

    # Clip it
    try:
        clip_path = clip_and_reformat_video(
            video_filepath=Path(local_video),
            start_time=start_time,
            end_time=end_time,
            output_path=Path("/tmp/clipped"),
            output_format=output_format,
        )
    except Exception as e:
        logging.error(
            f"Failed to clip and reformat video "
            f"(start: '{start_time}', end: '{end_time}', "
            f"format: '{output_format}'). Exception: {e}",
        )
        return abort(400)

    # Format the project id to the bucket
    bucket_name = f"{project_id}.appspot.com"

    # Generate save name
    save_path = f"{CLIP_STORAGE}/{uuid4()}"

    # Generate the save name
    try:
        return escape(
            upload_file_and_return_link(
                credentials_file=CREDENTIALS_PATH,
                bucket=bucket_name,
                filepath=str(clip_path),
                save_name=save_path,
            )
        )
    except Exception as e:
        logging.error(f"Failed to upload and create HTTPS link. Exception: {e}")
        return abort(400)
