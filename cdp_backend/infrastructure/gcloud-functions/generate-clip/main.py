#!/usr/bin/env python
# -*- coding: utf-8 -*-f

from pathlib import Path
from typing import Dict
from uuid import uuid4

import functions_framework
from flask import Request, escape
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
) -> str:
    if request_json and param in request_json:
        return request_json[param]
    if request_args and param in request_args:
        return request_args[param]

    raise ValueError(f"No param with name: '{param}'")


@functions_framework.http
def generate_clip_http(request: Request) -> str:
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

    # Unpack the params
    start_time = _unpack_param(request_json, request_args, "start")
    end_time = _unpack_param(request_json, request_args, "end")
    session_id = _unpack_param(request_json, request_args, "sessionId")
    out_format = _unpack_param(request_json, request_args, "format")
    project_id = _unpack_param(request_json, request_args, "projectId")

    # Download the session video
    local_video = download_video_from_session_id(
        credentials_file=CREDENTIALS_PATH,
        session_id=session_id,
        dest="/tmp/full-video"
    )

    # Clip it
    clip_path = clip_and_reformat_video(
        video_filepath=Path(local_video),
        start_time=start_time,
        end_time=end_time,
        out_format=out_format,
    )

    # Format the project id to the bucket
    bucket_name = f"{project_id}.appspot.com"

    # Generate save name
    save_path = f"{CLIP_STORAGE}/{uuid4()}"

    # Generate the save name
    return escape(
        upload_file_and_return_link(
            credentials_file=CREDENTIALS_PATH,
            bucket=bucket_name,
            filepath=str(clip_path),
            save_name=save_path,
        )
    )
