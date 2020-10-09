#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import List, NamedTuple

from fireo.models import Model
from fireo import fields

###############################################################################


class Order:
    ASCENDING = "ASCENDING"
    DESCENDING = "DESCENDING"


class IndexedField(NamedTuple):
    name: str
    order: str


class IndexedFieldSet(NamedTuple):
    fields: List[IndexedField]


###############################################################################

class Body(Model):
    name = fields.TextField(required=True)
    tag = fields.TextField()
    description = fields.TextField()
    start_date = fields.DateTime()
    end_date = fields.DateTime()
    is_active = fields.BooleanField()
    external_source_id = fields.TextField()

    @classmethod
    def get_example(cls):
        body = cls()
        body.name = "Full Council"
        body.is_active = True
        return body

    PRIMARY_KEYS = ["name"]
    INDEXES = []
