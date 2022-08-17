#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

import networkx as nx
import pytest
from fireo.fields import ReferenceField

from cdp_backend.bin.create_cdp_database_uml import _construct_dot_file
from cdp_backend.database import DATABASE_MODELS
from cdp_backend.database.models import Person

###############################################################################


def test_validate_model_definitions() -> None:
    for model_cls in DATABASE_MODELS:
        assert hasattr(model_cls, "Example")
        assert hasattr(model_cls, "_PRIMARY_KEYS")
        assert hasattr(model_cls, "_INDEXES")

        # Check fields for each model by using the Example
        m = model_cls.Example()
        for field_name, field in m._meta.field_list.items():
            # Assert that reference fields are suffixed with `_ref`
            if isinstance(field, ReferenceField):
                assert field_name.endswith("_ref")

            # Check that all primary keys are valid attributes of the model
            for pk in model_cls._PRIMARY_KEYS:
                assert hasattr(m, pk)

            # Check that all index fields are valid attributes of the model
            for idx_field_set in model_cls._INDEXES:
                for idx_field in idx_field_set.fields:
                    assert hasattr(m, idx_field.fieldPath)

            # Check that all primary keys are valid attributes of the model
            for pk in model_cls._PRIMARY_KEYS:
                assert hasattr(m, pk)


def test_cdp_database_model_has_no_cyclic_dependencies(tmpdir: Path) -> None:
    # Minor edits to:
    # https://blog.jasonantman.com/2012/03/python-script-to-find-dependency-cycles-in-graphviz-dot-files/

    # Create temp save location for dot file
    tmp_save_dot_path = str(Path(tmpdir) / "cdp_database_diagram.dot")

    # Create dot file
    _construct_dot_file(tmp_save_dot_path)

    # Read dot as networkx digraph
    G = nx.DiGraph(nx.drawing.nx_pydot.read_dot(tmp_save_dot_path))

    # Get cycles
    cycles = list(nx.simple_cycles(G))

    # Check for cycles
    if len(cycles) >= 1:
        raise ValueError(f"Found cyclic dependencies in CDP Database Model: {cycles}")


@pytest.mark.parametrize(
    "name, expected",
    [
        ("M. Lorena González", "m-lorena-gonzalez"),
        ("Example Person 256", "example-person-256"),
        ("lot's  of  spaces     ", "lots-of-spaces"),
    ],
)
def test_person_generate_router_string(name: str, expected: str) -> None:
    assert Person.generate_router_string(name) == expected
