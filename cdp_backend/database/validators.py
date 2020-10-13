#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from typing import Optional

from fireo.models import Model
from fsspec.core import url_to_fs

from . import exceptions

#############################################################################
# Model Validation


def model_is_unique(model: Model):
    """
    Validate that the primary keys of a to-be-uploaded-model are unique when compared
    to the collection.
    """
    # Initialize query
    query = model.__class__.collection

    # Loop and fill query for each primary key
    for pk in model._PRIMARY_KEYS:
        query.filter(pk, "==", getattr(model, pk))

    # Fetch and assert single value
    results = list(query.fetch())
    if len(results) >= 1:
        raise exceptions.UniquenessError(model=model, conflicting_results=results)


#############################################################################
# Field Validators


def router_string_is_valid(router_string: Optional[str]) -> bool:
    """
    Validate that the provided router string contains only lowercase alphabetic
    characters and optionally include a hyphen.

    None is a valid option.

    Parameters
    ----------
    router_string: Optional[str]
        The router string to validate.

    Returns
    -------
    status: bool
        The validation status.
    """
    if router_string is None:
        return True

    if re.match(r"^[a-z]+[\-]?[a-z]+$", router_string):
        return True

    return False


def email_is_valid(email: Optional[str]) -> bool:
    """
    Validate that a valid email was provided.

    None is a valid option.

    Parameters
    ----------
    email: Optional[str]
        The email to validate.

    Returns
    -------
    status: bool
        The validation status.
    """
    if email is None:
        return True

    if re.match(r"^[a-zA-Z0-9]+[\.]?[a-zA-Z0-9]+[@]\w+[.]\w{2,3}$", email):
        return True

    return False


def resource_exists(uri: Optional[str]) -> bool:
    """
    Validate that the URI provided points to an existing file.

    None is a valid option.

    Parameters
    ----------
    uri: Optional[str]
        The URI to validate resource existance for.

    Returns
    -------
    status: bool
        The validation status.
    """
    if uri is None:
        return True

    # Get file system
    fs, uri = url_to_fs(uri)

    # Check exists
    if fs.exists(uri):
        return True

    return False
