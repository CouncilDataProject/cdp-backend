#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
from typing import NamedTuple, Tuple

from fireo.models import Model
from fireo import fields

from . import validators
from ..utils import file_utils

###############################################################################


class Order:
    ASCENDING = "ASCENDING"
    DESCENDING = "DESCENDING"


class IndexedField(NamedTuple):
    name: str
    order: str


class IndexedFieldSet(NamedTuple):
    fields: Tuple[IndexedField]


###############################################################################


class File(Model):
    uri = fields.TextField(required=True)
    name = fields.TextField(required=True)
    description = fields.TextField()
    media_type = fields.TextField()

    @classmethod
    def get_example(cls):
        uri = "http://legistar2.granicus.com/seattle/attachments/02ba0302-6bd1-4eee-b9a2-6895f992e590.pdf"  # noqa: E501
        file = cls()
        file.uri = uri
        file.name = "Central Staff Memo"
        file.media_type = file_utils.get_media_type(uri)
        return file

    PRIMARY_KEYS = ("uri",)
    INDEXES = ()


class Person(Model):
    name = fields.TextField(required=True)
    router_string = fields.TextField(validator=validators.check_router_string)
    email = fields.TextField(validator=validators.check_email)
    phone = fields.NumberField()
    website = fields.TextField(validator=validators.check_resource_exists)
    picture_file = fields.ReferenceField(File)
    is_active = fields.BooleanField()
    external_source_id = fields.TextField()

    @classmethod
    def get_example(cls):
        person = cls()
        person.name = "M. Lorena González"
        person.router_string = "lorena-gonzalez"
        person.is_active = True
        return person

    PRIMARY_KEYS = (
        "name",
        "router_string",
    )
    INDEXES = ()


class Body(Model):
    name = fields.TextField(required=True)
    tag = fields.TextField()
    description = fields.TextField()
    start_datetime = fields.DateTime(required=True)
    end_datetime = fields.DateTime()
    is_active = fields.BooleanField()
    external_source_id = fields.TextField()

    @classmethod
    def get_example(cls):
        body = cls()
        body.name = "Full Council"
        body.is_active = True
        return body

    PRIMARY_KEYS = ("name",)
    INDEXES = ()


class Seat(Model):
    name = fields.TextField(required=True)
    electoral_area = fields.TextField()
    electoral_type = fields.TextField()
    map_file = fields.ReferenceField(File)
    external_source_id = fields.TextField()

    @classmethod
    def get_example(cls):
        seat = cls()
        seat.name = "Position 9"
        seat.electoral_area = "Citywide"
        seat.electoral_type = "at-large"
        return seat

    PRIMARY_KEYS = ("name",)
    INDEXES = ()


class Role(Model):
    title = fields.TextField(required=True)
    person = fields.ReferenceField(Person, required=True)
    body = fields.ReferenceField(Body, required=True)
    seat = fields.ReferenceField(Seat, required=True)
    start_datetime = fields.DateTime(required=True)
    end_datetime = fields.DateTime()
    external_source_id = fields.TextField()

    @classmethod
    def get_example(cls):
        role = cls()
        role.title = "Council President"
        role.person = Person.get_example()
        role.body = Body.get_example()
        role.seat = Seat.get_example()
        role.start_datetime = datetime.utcnow()
        return role

    PRIMARY_KEYS = ("title", "person", "body", "seat")
    INDEXES = ()
