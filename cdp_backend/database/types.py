#!/usr/bin/env python

from dataclasses import dataclass
from typing import List

from dataclasses_json import DataClassJsonMixin

###############################################################################


@dataclass
class IndexedField(DataClassJsonMixin):
    fieldPath: str  # noqa: N815
    order: str


@dataclass
class IndexedFieldSet(DataClassJsonMixin):
    fields: List[IndexedField]
