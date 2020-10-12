#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from typing import Optional

from fsspec.core import url_to_fs

#############################################################################


def check_router_string(router_string: Optional[str]) -> bool:
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


def check_email(email: Optional[str]) -> bool:
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


def check_resource_exists(uri: Optional[str]) -> bool:
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
