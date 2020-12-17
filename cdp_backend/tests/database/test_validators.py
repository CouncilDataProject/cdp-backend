#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
from typing import List
from unittest import mock

from cdp_backend.database import models, validators, exceptions
from fireo.models import Model

from .. import test_utils

#############################################################################


@pytest.mark.parametrize(
    "model_name, mock_return_values",
    [
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
def test_uniqueness_validation_exception(
    model_name: str,
    mock_return_values: List[Model],
) -> None:
    with mock.patch("fireo.queries.filter_query.FilterQuery.fetch") as mocked_fetch:
        mocked_fetch.return_value = mock_return_values

        # Get model spec from models module
        spec = getattr(models, model_name)

        # Get instance of model
        instance = spec.Example()

        # Validate
        validators.model_is_unique(instance)


@pytest.mark.parametrize(
    "model_name, mock_return_values, expected",
    [
        ("Body", [], True),
        ("Person", [], True),
    ],
)
def test_uniqueness_validation_is_unique(
    model_name: str,
    mock_return_values: List[Model],
    expected: bool,
) -> None:
    with mock.patch("fireo.queries.filter_query.FilterQuery.fetch") as mocked_fetch:
        mocked_fetch.return_value = mock_return_values

        # Get model spec from models module
        spec = getattr(models, model_name)

        # Get instance of model
        instance = spec.Example()

        # Validate
        assert expected == validators.model_is_unique(instance)


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
def test_router_string_is_valid(router_string: str, expected_result: bool) -> None:
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
def test_email_is_valid(email: str, expected_result: bool) -> None:
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
def test_local_resource_exists(uri: str, expected_result: bool) -> None:
    actual_result = validators.resource_exists(uri)
    assert actual_result == expected_result


@pytest.mark.skipif(
    not test_utils.internet_is_available(),
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
def test_remote_resource_exists(uri: str, expected_result: bool) -> None:
    actual_result = validators.resource_exists(uri)
    assert actual_result == expected_result
