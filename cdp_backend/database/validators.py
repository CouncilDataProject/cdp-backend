#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from typing import Optional

from fsspec.core import url_to_fs

#############################################################################


def check_router_string(router_string: Optional[str]) -> bool:
    if router_string is None:
        return True

    if re.match(r"^[a-z]+[\-]?[a-z]+$", router_string):
        return True

    return False


def check_email(email: Optional[str]) -> bool:
    if email is None:
        return True

    if re.match(r"^[a-zA-Z0-9]+[\.]?[a-zA-Z0-9]+[@]\w+[.]\w{2,3}$", email):
        return True

    return False


def check_resource_exists(uri: Optional[str]) -> bool:
    if uri is None:
        return True

    # Get file system
    fs, uri = url_to_fs(uri)

    # Check exists
    if fs.exists(uri):
        return True

    return False
