#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import NamedTuple, Tuple

###############################################################################


class IndexedField(NamedTuple):
    name: str
    order: str


class IndexedFieldSet(NamedTuple):
    fields: Tuple[IndexedField, ...]
