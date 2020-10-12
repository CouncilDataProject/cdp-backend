#!/usr/bin/env python
# -*- coding: utf-8 -*-

import inspect

from fireo.fields import ReferenceField

from cdp_backend.database import models

###############################################################################


def test_validate_model_definitions():
    for model_name, cls in inspect.getmembers(models, inspect.isclass):
        if model_name not in ["Model", "datetime"]:
            assert hasattr(cls, "Example")
            assert hasattr(cls, "_PRIMARY_KEYS")
            assert hasattr(cls, "_INDEXES")

            # Check fields for each model by using the Example
            m = cls.Example()
            for field_name, field in m._meta.field_list.items():
                # Assert that reference fields are suffixed with `_ref`
                if isinstance(field, ReferenceField):
                    assert field_name.endswith("_ref")
