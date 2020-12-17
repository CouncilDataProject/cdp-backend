#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
from typing import Optional

from fireo.models import Model
from fsspec.core import url_to_fs

from ..utils.constants_utils import get_all_class_attributes
from .types import EventMinutesItemDecision, VoteDecision

###############################################################################

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)4s: %(module)s:%(lineno)4s %(asctime)s] %(message)s",
)
log = logging.getLogger(__name__)

###############################################################################
# Model Validation


def model_is_unique(model: Model) -> bool:
    """
    Validate that the primary keys of a to-be-uploaded model are unique when compared
    to the collection.

    Parameters
    ----------
    model: Model
        A to-be-uploaded model instance.

    Returns
    -------
    is_unique: bool
        Boolean representing if the model is unique in the collection.

    Examples
    --------
    >>> from cdp_backend.database import models
    ... from cdp_backend.database.validators import model_is_unique
    ...
    ... b = models.Body.Example()
    ... if model_is_unique(b):
    ...     b.save()
    """
    # Initialize query
    query = model.__class__.collection

    # Loop and fill query for each primary key
    for pk in model._PRIMARY_KEYS:
        query = query.filter(pk, "==", getattr(model, pk))

    # Fetch and assert single value
    results = list(query.fetch())
    if len(results) >= 1:
        log.info(f"Found conflicting results={results} for model={model}.")
        return False

    return True


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

    # Check only lowercase and hyphen allowed
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


def vote_decision_is_valid(decision: str) -> bool:
    """
    Validate that vote's decision is valid.

    None is not a valid option.

    Parameters
    ----------
    decision: str
        The decision to validate.

    Returns
    -------
    status: bool
        The validation status.
    """
    return decision in get_all_class_attributes(VoteDecision)


def event_minutes_item_decision_is_valid(decision: Optional[str]) -> bool:
    """
    Validate that event minutes item's decision is valid.

    None is a valid option.

    Parameters
    ----------
    decision: str
        The decision to validate.

    Returns
    -------
    status: bool
        The validation status.
    """
    if decision:
        return decision in get_all_class_attributes(EventMinutesItemDecision)
    return True
