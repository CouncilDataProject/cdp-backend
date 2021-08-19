#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
from dataclasses import dataclass
from typing import Callable, List, Optional, Type

from fireo.models import Model
from fsspec.core import url_to_fs

from ..utils.constants_utils import get_all_class_attr_values

###############################################################################

log = logging.getLogger(__name__)

###############################################################################
# Model Validation


@dataclass(frozen=True)
class UniquenessValidation:
    """
    An object containing uniqueness data of a database model object.

    Parameters
    ----------
    is_unique: bool
        A boolean on whether the model is unique by primary key
        in the database collection.

    conflicting_models: List[Model]
        All existing models that share the same primary keys as the input model.
    """

    is_unique: bool
    conflicting_models: List[Model]


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
    if re.match(r"^[a-z0-9\-]+$", router_string):
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

    # TODO Replace after finding way to pass custom fs through FireO validator
    if uri.startswith("gs://") or uri.startswith("https://storage.googleapis"):
        return True

    else:
        # Get file system
        fs, uri = url_to_fs(uri)

        # Check exists
        if fs.exists(uri):
            return True

    return False


def create_constant_value_validator(
    constant_cls: Type, is_required: bool
) -> Callable[[str], bool]:
    """
    Create a validator func that validates a value is one of the valid values.

    Parameters
    ----------
    constant_cls: Type
        The constant class that contains the valid values.
    is_required: bool
        Whether the value is required.

    Returns
    -------
    validator_func: Callable[[str], bool]
        The validator func.
    """

    def is_valid(value: str) -> bool:
        """
        Validate that value is valid.

        Parameters
        ----------
        value: str
            The value to validate.

        Returns
        -------
        status: bool
            The validation status.
        """
        if value is None:
            return not is_required
        return value in get_all_class_attr_values(constant_cls)

    return is_valid
