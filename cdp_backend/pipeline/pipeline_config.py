#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from dataclasses import dataclass, field
from typing import Optional

from dataclasses_json import dataclass_json
from gcsfs import GCSFileSystem

###############################################################################


@dataclass_json
@dataclass
class EventGatherPipelineConfig:
    """
    Configuration options for the CDP event gather pipeline.

    Parameters
    ----------
    google_credentials_file: str
        Path to the Google Service Account Credentials JSON file.
    get_events_function_path: str
        Path to the function (including function name) that supplies event data to the
        CDP event gather pipeline.
    gcs_bucket_name: Optional[str]
        The name of the Google Storage bucket for CDP generated files.
        Default: None (parse from the Google Service Account Credentials JSON file)
    caption_new_speaker_turn_pattern: Optional[str]
        Passthrough to sr_models.webvtt_sr_model.WebVTTSRModel.
    caption_confidence: Optional[float]
        Passthrough to sr_models.webvtt_sr_model.WebVTTSRModel.
    """

    google_credentials_file: str
    get_events_function_path: str
    gcs_bucket_name: Optional[str] = None
    _validated_gcs_bucket_name: Optional[str] = field(
        init=False,
        repr=False,
        default=None,
    )
    caption_new_speaker_turn_pattern: Optional[str] = None
    caption_confidence: Optional[float] = None

    @property
    def validated_gcs_bucket_name(self) -> str:
        if self._validated_gcs_bucket_name is None:
            if self.gcs_bucket_name is not None:
                bucket = self.gcs_bucket_name

            else:
                # Open the key to get the project id
                with open(self.google_credentials_file, "r") as open_resource:
                    creds = json.load(open_resource)
                    project_id = creds["project_id"]

                # Remove all files in bucket
                bucket = f"{project_id}.appspot.com"

            # Validate
            fs = GCSFileSystem(token=self.google_credentials_file)
            try:
                fs.ls(bucket)
                self._validated_gcs_bucket_name = bucket

            except FileNotFoundError:
                raise ValueError(
                    f"Provided or infered GCS bucket name does not exist. ('{bucket}')"
                )

        return self._validated_gcs_bucket_name
