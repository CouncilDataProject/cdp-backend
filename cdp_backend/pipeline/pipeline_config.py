#!/usr/bin/env python

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

from dataclasses_json import DataClassJsonMixin
from gcsfs import GCSFileSystem

###############################################################################


@dataclass
class EventGatherPipelineConfig(DataClassJsonMixin):
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
    whisper_model_name: str
        Passthrough to sr_models.whisper.WhisperModel.
    whisper_model_confidence: Optional[float]
        Passthrough to sr_models.whisper.WhisperModel.
    default_event_gather_from_days_timedelta: int
        Default number of days to subtract from current time to then pass to the
        provided get_events function as the `from_dt` datetime.
        Default: 2 (from_dt will be set to current datetime - 2 days)
    """

    google_credentials_file: str
    get_events_function_path: str
    gcs_bucket_name: Optional[str] = None
    _validated_gcs_bucket_name: Optional[str] = field(
        init=False,
        repr=False,
        default=None,
    )
    whisper_model_name: str = "medium"
    whisper_model_confidence: Optional[float] = None
    default_event_gather_from_days_timedelta: int = 2

    @property
    def validated_gcs_bucket_name(self) -> str:
        """GCS bucket name after it has been validated to exist."""
        if self._validated_gcs_bucket_name is None:
            if self.gcs_bucket_name is not None:
                bucket = self.gcs_bucket_name

            else:
                # Open the key to get the project id
                with open(self.google_credentials_file) as open_resource:
                    creds = json.load(open_resource)
                    project_id = creds["project_id"]

                # Remove all files in bucket
                bucket = f"{project_id}.appspot.com"

            # Validate
            fs = GCSFileSystem(token=self.google_credentials_file)
            try:
                fs.ls(bucket)
                self._validated_gcs_bucket_name = bucket

            except FileNotFoundError as e:
                raise ValueError(
                    f"Provided or infered GCS bucket name does not exist. ('{bucket}')"
                ) from e

        return self._validated_gcs_bucket_name


@dataclass
class EventIndexPipelineConfig(DataClassJsonMixin):
    """
    Configuration options for the CDP event index pipeline.

    Parameters
    ----------
    google_credentials_file: str
        Path to the Google Service Account Credentials JSON file.
    gcs_bucket_name: Optional[str]
        The name of the Google Storage bucket for CDP generated files.
        Default: None (parse from the Google Service Account Credentials JSON file)
    datetime_weighting_days_decay: int
        The number of days that grams from an event should be labeled as more relevant.
        Default: 30 (grams from events less than 30 days old will generally be valued
        higher than their pure relevance score)
    local_storage_dir: Union[str, Path]
        The local storage directory to store the chunked index prior to upload.
        Default: "index/" (current working directory / index)
    """

    google_credentials_file: str
    gcs_bucket_name: Optional[str] = None
    _validated_gcs_bucket_name: Optional[str] = field(
        init=False,
        repr=False,
        default=None,
    )
    datetime_weighting_days_decay: int = 30
    local_storage_dir: Union[str, Path] = "index/"

    @property
    def validated_gcs_bucket_name(self) -> str:
        """GCS bucket name after it has been validated to exist."""
        if self._validated_gcs_bucket_name is None:
            if self.gcs_bucket_name is not None:
                bucket = self.gcs_bucket_name

            else:
                # Open the key to get the project id
                with open(self.google_credentials_file) as open_resource:
                    creds = json.load(open_resource)
                    project_id = creds["project_id"]

                # Remove all files in bucket
                bucket = f"{project_id}.appspot.com"

            # Validate
            fs = GCSFileSystem(token=self.google_credentials_file)
            try:
                fs.ls(bucket)
                self._validated_gcs_bucket_name = bucket

            except FileNotFoundError as e:
                raise ValueError(
                    f"Provided or infered GCS bucket name does not exist. ('{bucket}')"
                ) from e

        return self._validated_gcs_bucket_name
