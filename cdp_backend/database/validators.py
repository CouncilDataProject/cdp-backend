#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

#############################################################################


def check_email(email: str) -> bool:
    if re.match(r"^[a-zA-Z0-9]+[\.]?[a-zA-Z0-9]+[@]\w+[.]\w{2,3}$", email):
        return True

    return (False, "Invalid email provided")
