#!/usr/bin/env python

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Callable

import backoff
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
    conflicting_models: list[Model]


#############################################################################
# Field Validators


def router_string_is_valid(router_string: str | None) -> bool:
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


def time_duration_is_valid(time_duration: str | None) -> bool:
    """
    Validate that the provided time duration string is acceptable to FFmpeg.
    The validator is unnecessarily limited to HH:MM:SS. The spec is a little
    more flexible.

    None is a valid option.

    Parameters
    ----------
    time_duration: Optional[str]
        The time duration to validate.

    Returns
    -------
    status: bool
        The validation status.
    """
    if time_duration is None:
        return True

    # HH:MM:SS
    if re.match(r"^((((\d{1,2}:)?[0-5])?\d:)?[0-5])?\d$", time_duration):
        return True

    return False


def email_is_valid(email: str | None) -> bool:
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


@backoff.on_exception(
    backoff.expo,
    requests.exceptions.ConnectTimeout,
    max_tries=3,
)
def resource_exists(uri: str | None, **kwargs: Any) -> bool:  # noqa: C901
    """
    Validate that the URI provided points to an existing file.

    None is a valid option.

    Parameters
    ----------
    uri: Optional[str]
        The URI to validate resource existance for.
    kwargs: Any
        Any extra arguments needed for resource retrieval.
        I.e. google_credentials_file.

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
            r = requests.head(uri, verify=False)

            return r.status_code == requests.codes.ok
        except requests.exceptions.SSLError:
            return False

    # Get any filesystem and try
    try:
        fs, path = url_to_fs(uri)
        return fs.exists(path)
    except Exception:
        return False


def create_constant_value_validator(constant_cls: type) -> Callable[[str], bool]:
    """
    Create a validator func that validates a value is one of the valid values.

    Parameters
    ----------
    constant_cls: Type
        The constant class that contains the valid values.

    Returns
    -------
    validator_func: Callable[[str], bool]
        The validator func.

    Notes
    -----
    Will always allow `None` as a valid option.
    To remove `None` as a viable input, set the database model field `required=True`.

    See: https://github.com/CouncilDataProject/cdp-backend/pull/164
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
        return value is None or value in get_all_class_attr_values(constant_cls)

    return is_valid


def try_url(url: str, resolve_func: Callable = resource_exists) -> str:
    """
    Given a URL, return the URL with the protocol that exists (http or https)
    with a preference for https.

    Parameters
    ----------
    url: str
        The target resource url.
    resolve_func: func(url: str) -> bool
        A function that takes in a str URL and determines whether it is reachable.
        Default is our "resource_exists" func

    Returns
    -------
    resource_url: str
        The url with the correct protocol based on where the resource exists.
        If does not exist, a LookupError is raised.
    """
    secure_url = url.replace("http://", "https://")
    if resolve_func(secure_url):
        return secure_url

    if resolve_func(url):
        return url

    raise LookupError(f"the resource {url} could not be found")


def is_secure_uri(url: str) -> bool:
    return url.startswith("https://")
