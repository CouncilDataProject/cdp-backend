# -*- coding: utf-8 -*-

"""Database package for cdp_backend."""

import inspect

import fireo

from . import models

###############################################################################


DATABASE_MODELS = []
for _, model_cls in inspect.getmembers(models, inspect.isclass):
    if isinstance(model_cls, fireo.models.model_meta.ModelMeta):
        DATABASE_MODELS.append(model_cls)

# Remove the base fireo Model as it itself inherits from ModelMeta
DATABASE_MODELS.remove(fireo.models.model.Model)

# We sort by name to always have the same order for testing and infrastructure building
DATABASE_MODELS = sorted(DATABASE_MODELS, key=lambda m: m.collection_name)
