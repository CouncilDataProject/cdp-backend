#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
from typing import Union
from unittest import mock
from unittest.mock import MagicMock

import pytest

from cdp_backend.pipeline.pipeline_config import (
    EventGatherPipelineConfig,
    EventIndexPipelineConfig,
)

#############################################################################

# NOTE:
# unittest mock patches are accesible in reverse order in params
# i.e. if we did the following patches
# @patch(module.func_a)
# @patch(module.func_b)
#
# the param order for the magic mocks would be
# def test_module(func_b, func_a):
#
# great system stdlib :upsidedownface:

FAKE_CREDS_PATH = str(
    (Path(__file__).parent.parent / "resources" / "fake_creds.json").absolute()
)

#############################################################################


@mock.patch("gcsfs.credentials.GoogleCredentials.connect")
@mock.patch("gcsfs.GCSFileSystem.ls")
@pytest.mark.parametrize(
    "bucket_exists, config, expected_bucket_name",
    [
        # Test event gather pipeline config
        (
            True,
            EventGatherPipelineConfig(
                google_credentials_file=FAKE_CREDS_PATH,
                get_events_function_path="doesnt.matter",
            ),
            "fake-project.appspot.com",
        ),
        (
            True,
            EventGatherPipelineConfig(
                google_credentials_file=FAKE_CREDS_PATH,
                get_events_function_path="doesnt.matter",
                gcs_bucket_name="hello-world",
            ),
            "hello-world",
        ),
        # Test for corrupted creds or not setup infra
        pytest.param(
            False,
            EventGatherPipelineConfig(
                google_credentials_file=FAKE_CREDS_PATH,
                get_events_function_path="doesnt.matter",
            ),
            None,
            marks=pytest.mark.raises(exception=ValueError),
        ),
        # Test for invalid _explicit_ bucket
        pytest.param(
            False,
            EventGatherPipelineConfig(
                google_credentials_file=FAKE_CREDS_PATH,
                get_events_function_path="doesnt.matter",
                gcs_bucket_name="hello-world",
            ),
            None,
            marks=pytest.mark.raises(exception=ValueError),
        ),
        #######################################################################
        # Test event index pipeline config
        (
            True,
            EventIndexPipelineConfig(
                google_credentials_file=FAKE_CREDS_PATH,
            ),
            "fake-project.appspot.com",
        ),
        (
            True,
            EventIndexPipelineConfig(
                google_credentials_file=FAKE_CREDS_PATH,
                gcs_bucket_name="hello-world",
            ),
            "hello-world",
        ),
        # Test for corrupted creds or not setup infra
        pytest.param(
            False,
            EventIndexPipelineConfig(
                google_credentials_file=FAKE_CREDS_PATH,
            ),
            None,
            marks=pytest.mark.raises(exception=ValueError),
        ),
        # Test for invalid _explicit_ bucket
        pytest.param(
            False,
            EventIndexPipelineConfig(
                google_credentials_file=FAKE_CREDS_PATH,
                gcs_bucket_name="hello-world",
            ),
            None,
            marks=pytest.mark.raises(exception=ValueError),
        ),
    ],
)
def test_config_construction(
    mock_gcsfs_ls: MagicMock,
    mock_google_credentials_connect: MagicMock,
    bucket_exists: bool,
    config: Union[EventGatherPipelineConfig, EventIndexPipelineConfig],
    expected_bucket_name: str,
) -> None:
    if bucket_exists:
        mock_gcsfs_ls.return_value = []
    else:
        mock_gcsfs_ls.side_effect = FileNotFoundError()

    assert config.validated_gcs_bucket_name == expected_bucket_name
