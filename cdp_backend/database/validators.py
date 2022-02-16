#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
from dataclasses import dataclass
from typing import Callable, List, Optional, Type

import requests
from fireo.models import Model
from fsspec.core import url_to_fs
from gcsfs import GCSFileSystem

from ..utils.constants_utils import get_all_class_attr_values
from ..utils.string_utils import convert_gcs_json_url_to_gsutil_form

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


def resource_exists(uri: Optional[str], **kwargs: str) -> bool:
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

    if uri.startswith("gs://") or uri.startswith("https://storage.googleapis"):
        # Convert to gsutil form if necessary
        if uri.startswith("https://storage.googleapis"):
            uri = convert_gcs_json_url_to_gsutil_form(uri)

            # If uri is not convertible to gsutil form we can't confirm
            if uri == "":
                return False

        if kwargs.get("google_credentials_file"):
            fs = GCSFileSystem(token=str(kwargs.get("google_credentials_file", "anon")))
            return fs.exists(uri)

        # Can't check GCS resources without creds file
        else:
            try:
                anon_fs = GCSFileSystem(token="anon")
                return anon_fs.exists(uri)
            except Exception:
                return False

    # Is HTTP remote resource
    elif uri.startswith("http"):
        try:
            # Use HEAD request to check if remote resource exists
            r = requests.head(uri)

            return r.status_code == requests.codes.ok
        except requests.exceptions.SSLError:
            return False

    # Get any filesystem and try
    try:
        fs, path = url_to_fs(uri)
        return fs.exists(path)
    except Exception:
        return False


def create_constant_value_validator(
    constant_cls: Type, allow_none: bool
) -> Callable[[str], bool]:
    """
    Create a validator func that validates a value is one of the valid values.

    Parameters
    ----------
    constant_cls: Type
        The constant class that contains the valid values.
    allow_none: bool
        Whether to allow `None` as a valid value for this field.

    Returns
    -------
    validator_func: Callable[[str], bool]
        The validator func.

    Notes
    -----
    If the field the created validation function is attached to is optional,
    (i.e. required=True, is not set) `allow_none` should be set to True.
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
        allowed_attrs = get_all_class_attr_values(constant_cls)
        if allow_none:
            allowed_attrs.append(None)

        return value in allowed_attrs

    return is_valid
