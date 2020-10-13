#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
from unittest import mock

from cdp_backend.database import models, validators, exceptions

from .. import test_utils

#############################################################################


@pytest.mark.parametrize(
    "model_name, mock_return_values",
    [
        ("Body", []),
        pytest.param(
            "Body",
            [models.Body.Example()],
            marks=pytest.mark.raises(exception=exceptions.UniquenessError),
        ),
        pytest.param(
            "Body",
            [models.Body.Example(), models.Body.Example()],
            marks=pytest.mark.raises(exception=exceptions.UniquenessError),
        ),
        pytest.param(
            "Person",
            [models.Person.Example()],
            marks=pytest.mark.raises(exception=exceptions.UniquenessError),
        ),
    ],
)
def test_uniqueness_validation(model_name, mock_return_values):
    with mock.patch("fireo.managers.managers.Manager.fetch") as mocked_fetch:
        mocked_fetch.return_value = mock_return_values

        # Get example from model
        m = getattr(models, model_name).Example()
        validators.model_is_unique(m)


@pytest.mark.parametrize(
    "router_string, expected_result",
    [
        (None, True),
        ("lorena-gonzalez", True),
        ("lorena", True),
        ("LORENA", False),
        ("gonzález", False),
        ("lorena_gonzalez", False),
        ("lorena gonzalez", False),
    ],
)
def test_router_string_is_valid(router_string, expected_result):
    actual_result = validators.router_string_is_valid(router_string)
    assert actual_result == expected_result


@pytest.mark.parametrize(
    "email, expected_result",
    [
        (None, True),
        ("Lorena.Gonzalez@seattle.gov", True),
        ("lorena.gonzalez@seattle.gov", True),
        ("Lorena.gov", False),
        ("Lorena@", False),
        ("Lorena@seattle", False),
        ("Lorena Gonzalez@seattle", False),
        ("Lorena.González@seattle.gov", False),
    ],
)
def test_email_is_valid(email, expected_result):
    actual_result = validators.email_is_valid(email)
    assert actual_result == expected_result


@pytest.mark.parametrize(
    "uri, expected_result",
    [
        (None, True),
        (__file__, True),
        ("file://does-not-exist.txt", False),
    ],
)
def test_local_resource_exists(uri, expected_result):
    actual_result = validators.resource_exists(uri)
    assert actual_result == expected_result


@pytest.mark.skipif(
    not test_utils.check_internet_available(),
    reason="No internet connection",
)
@pytest.mark.parametrize(
    "uri, expected_result",
    [
        (None, True),
        ("https://docs.pytest.org/en/latest/index.html", True),
        ("https://docs.pytest.org/en/latest/does-not-exist.html", False),
    ],
)
def test_remote_resource_exists(uri, expected_result):
    actual_result = validators.resource_exists(uri)
    assert actual_result == expected_result
