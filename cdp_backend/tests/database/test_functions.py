#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
from fireo.models import Model

from cdp_backend.database import functions as db_functions
from cdp_backend.database import models as db_models

###############################################################################
# Tests

body_a = db_models.Body()
body_a.name = "Body A"

body_b = db_models.Body()
body_b.name = "Body B"


@pytest.mark.parametrize(
    "model, expected_id",
    [
        # General examples and testing recursive id gen
        (db_models.Body.Example(), "4346a8351006"),
        (db_models.Person.Example(), "e54faa3434c9"),
        (db_models.MinutesItem.Example(), "1e575caea0b9"),
        # Testing models differ
        (body_a, "0a8a8e139258"),
        (body_b, "1535fef479ff"),
    ],
)
def test_generate_and_attach_doc_hash_as_id(model: Model, expected_id: str) -> None:
    updated_model = db_functions.generate_and_attach_doc_hash_as_id(model)
    assert updated_model.id == expected_id


###############################################################################

# Only test functions that do something besides parameter unpacking and assigning
# Mypy can type check for us so no real need to have tedious tests for every
# db model creation function.

# Attribute unpacking and setting gets tested in event pipeline tests.


@pytest.mark.parametrize(
    "uri, expected_name, expected_uri",
    [
        ("ex://name.ext", "name.ext", "ex://name.ext"),
        (
            "fake://test/multi/path/file.ext",
            "file.ext",
            "fake://test/multi/path/file.ext",
        ),
        ("okay://no-file-ext", "no-file-ext", "okay://no-file-ext"),
    ],
)
def test_create_file(uri: str, expected_name: str, expected_uri: str) -> None:
    db_file = db_functions.create_file(uri)

    assert db_file.name == expected_name
    assert db_file.uri == expected_uri
