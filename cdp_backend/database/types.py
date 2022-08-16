#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from typing import List

from dataclasses_json import DataClassJsonMixin

###############################################################################


@dataclass
class IndexedField(DataClassJsonMixin):
    fieldPath: str
    order: str


@dataclass
class IndexedFieldSet(DataClassJsonMixin):
    fields: List[IndexedField]
