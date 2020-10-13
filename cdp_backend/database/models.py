#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime

from fireo.models import Model
from fireo import fields

from . import validators
from ..utils import file_utils

###############################################################################


class File(Model):
    """
    A file from the CDP file store.
    """

    uri = fields.TextField(required=True, validator=validators.resource_exists)
    name = fields.TextField(required=True)
    description = fields.TextField()
    media_type = fields.TextField()

    @classmethod
    def Example(cls):
        uri = "gs://cdp-example/central-staff-memo.pdf"
        file = cls()
        file.uri = uri
        file.name = "Central Staff Memo"
        file.media_type = file_utils.get_media_type(uri)
        return file

    _PRIMARY_KEYS = ("uri",)
    _INDEXES = ()


class Person(Model):
    """
    Primarily the council members, this could technically include the mayor or city
    manager, or any other "normal" presenters and attendees of meetings.
    """

    name = fields.TextField(required=True)
    router_string = fields.TextField(validator=validators.router_string_is_valid)
    email = fields.TextField(validator=validators.email_is_valid)
    phone = fields.NumberField()
    website = fields.TextField(validator=validators.resource_exists)
    picture_ref = fields.ReferenceField(File)
    is_active = fields.BooleanField()
    external_source_id = fields.TextField()

    @classmethod
    def Example(cls):
        person = cls()
        person.name = "M. Lorena González"
        person.router_string = "lorena-gonzalez"
        person.is_active = True
        return person

    _PRIMARY_KEYS = (
        "name",
        "router_string",
    )
    _INDEXES = ()


class Body(Model):
    """
    A meeting body. This can be full council, a subcommittee, or "off-council" matters
    such as election debates.
    """

    name = fields.TextField(required=True)
    tag = fields.TextField()
    description = fields.TextField()
    start_datetime = fields.DateTime(required=True)
    end_datetime = fields.DateTime()
    is_active = fields.BooleanField()
    external_source_id = fields.TextField()

    @classmethod
    def Example(cls):
        body = cls()
        body.name = "Full Council"
        body.is_active = True
        body.start_datetime = datetime.utcnow()
        return body

    _PRIMARY_KEYS = ("name",)
    _INDEXES = ()


class Seat(Model):
    """
    An electable office on the City Council. I.E. "Position 9".
    """

    name = fields.TextField(required=True)
    electoral_area = fields.TextField()
    electoral_type = fields.TextField()
    image_ref = fields.ReferenceField(File)
    external_source_id = fields.TextField()

    @classmethod
    def Example(cls):
        seat = cls()
        seat.name = "Position 9"
        seat.electoral_area = "Citywide"
        seat.electoral_type = "at-large"
        return seat

    _PRIMARY_KEYS = ("name",)
    _INDEXES = ()


class Role(Model):
    """
    A role is a person's job for a period of time in the city council. A person can
    (and should) have multiple roles. For example: a person has two terms as city
    council member for district four then a term as city council member for a citywide
    seat. Roles can also be tied to committee chairs. For example: a council member
    spends a term on the transportation committee and then spends a term on the finance
    committee.
    """

    title = fields.TextField(required=True)
    person_ref = fields.ReferenceField(Person, required=True)
    body_ref = fields.ReferenceField(Body, required=True)
    seat_ref = fields.ReferenceField(Seat, required=True)
    start_datetime = fields.DateTime(required=True)
    end_datetime = fields.DateTime()
    external_source_id = fields.TextField()

    @classmethod
    def Example(cls):
        role = cls()
        role.title = "Council President"
        role.person_ref = Person.Example()
        role.body_ref = Body.Example()
        role.seat_ref = Seat.Example()
        role.start_datetime = datetime.utcnow()
        return role

    _PRIMARY_KEYS = ("title", "person", "body", "seat")
    _INDEXES = ()
