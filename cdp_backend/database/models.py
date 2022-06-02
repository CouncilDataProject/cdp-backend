#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import unicodedata
from datetime import datetime
from typing import Dict

from fireo import fields
from fireo.models import Model

from ..utils import file_utils
from . import validators
from .constants import (
    EventMinutesItemDecision,
    MatterStatusDecision,
    Order,
    RoleTitle,
    VoteDecision,
)
from .types import IndexedField, IndexedFieldSet

###############################################################################


class File(Model):
    """
    A file from the CDP file store.
    """

    id = fields.IDField()
    uri = fields.TextField(required=True, validator=validators.resource_exists)
    name = fields.TextField(required=True)
    description = fields.TextField()
    media_type = fields.TextField()

    class Meta:
        ignore_none_field = False

    def set_validator_kwargs(self, kwargs: Dict) -> None:
        field = fields.TextField(
            required=True, validator=validators.resource_exists, validator_kwargs=kwargs
        )

        field.contribute_to_model(File, "uri")

    @classmethod
    def Example(cls) -> Model:
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

    id = fields.IDField()
    name = fields.TextField(required=True)
    router_string = fields.TextField(
        required=True, validator=validators.router_string_is_valid
    )
    email = fields.TextField(validator=validators.email_is_valid)
    phone = fields.TextField()
    website = fields.TextField(validator=validators.resource_exists)
    picture_ref = fields.ReferenceField(File, auto_load=False)
    is_active = fields.BooleanField(required=True)
    external_source_id = fields.TextField()

    class Meta:
        ignore_none_field = False

    def set_validator_kwargs(self, kwargs: Dict) -> None:
        field = fields.TextField(
            validator=validators.resource_exists,
            validator_kwargs=kwargs,
        )

        field.contribute_to_model(Person, "website")

    @classmethod
    def Example(cls) -> Model:
        person = cls()
        person.name = "M. Lorena González"
        person.router_string = "lorena-gonzalez"
        person.is_active = True
        return person

    _PRIMARY_KEYS = ("name",)
    _INDEXES = ()

    @staticmethod
    def strip_accents(name: str) -> str:
        return "".join(
            char
            for char in unicodedata.normalize("NFKD", name)
            if unicodedata.category(char) != "Mn"
        )

    @staticmethod
    def generate_router_string(name: str) -> str:
        non_accented = Person.strip_accents(name)
        char_cleaner = re.compile(r"[^a-zA-Z0-9\s\-]")
        char_cleaned = re.sub(char_cleaner, "", non_accented)
        whitespace_cleaner = re.compile(r"[\s]+")
        whitespace_cleaned = re.sub(whitespace_cleaner, " ", char_cleaned)
        spaces_replaced = whitespace_cleaned.replace(" ", "-")
        if spaces_replaced[-1] == "-":
            fully_cleaned = spaces_replaced[:-1]
        else:
            fully_cleaned = spaces_replaced

        return fully_cleaned.lower()


class Body(Model):
    """
    A meeting body. This can be full council, a subcommittee, or "off-council" matters
    such as election debates.
    """

    id = fields.IDField()
    name = fields.TextField(required=True)
    description = fields.TextField()
    start_datetime = fields.DateTime(required=True)
    end_datetime = fields.DateTime()
    is_active = fields.BooleanField(required=True)
    external_source_id = fields.TextField()

    class Meta:
        ignore_none_field = False

    @classmethod
    def Example(cls) -> Model:
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

    id = fields.IDField()
    name = fields.TextField(required=True)
    electoral_area = fields.TextField()
    electoral_type = fields.TextField()
    image_ref = fields.ReferenceField(File, auto_load=False)
    external_source_id = fields.TextField()

    class Meta:
        ignore_none_field = False

    @classmethod
    def Example(cls) -> Model:
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
    (and generally does) have many roles. For example: a person has two terms as city
    council member for district four then a term as city council member for a citywide
    seat. Roles can also be tied to committee chairs. For example: a council member
    spends a term on the transportation committee and then spends a term on the finance
    committee.
    """

    id = fields.IDField()
    title = fields.TextField(
        required=True,
        validator=validators.create_constant_value_validator(RoleTitle),
    )
    person_ref = fields.ReferenceField(Person, required=True, auto_load=False)
    body_ref = fields.ReferenceField(Body, auto_load=False)
    seat_ref = fields.ReferenceField(Seat, required=True, auto_load=False)
    start_datetime = fields.DateTime(required=True)
    end_datetime = fields.DateTime()
    external_source_id = fields.TextField()

    class Meta:
        ignore_none_field = False

    @classmethod
    def Example(cls) -> Model:
        role = cls()
        role.title = RoleTitle.COUNCILPRESIDENT
        role.person_ref = Person.Example()
        role.body_ref = Body.Example()
        role.seat_ref = Seat.Example()
        role.start_datetime = datetime.utcnow()
        return role

    _PRIMARY_KEYS = ("title", "person_ref", "body_ref", "seat_ref")
    _INDEXES = (
        IndexedFieldSet(
            (
                IndexedField(name="person_ref", order=Order.ASCENDING),
                IndexedField(name="start_datetime", order=Order.ASCENDING),
            )
        ),
        IndexedFieldSet(
            (
                IndexedField(name="person_ref", order=Order.ASCENDING),
                IndexedField(name="start_datetime", order=Order.DESCENDING),
            )
        ),
        IndexedFieldSet(
            (
                IndexedField(name="person_ref", order=Order.ASCENDING),
                IndexedField(name="end_datetime", order=Order.ASCENDING),
            )
        ),
        IndexedFieldSet(
            (
                IndexedField(name="person_ref", order=Order.ASCENDING),
                IndexedField(name="end_datetime", order=Order.DESCENDING),
            )
        ),
        IndexedFieldSet(
            (
                IndexedField(name="seat_ref", order=Order.ASCENDING),
                IndexedField(name="end_datetime", order=Order.DESCENDING),
            )
        ),
        IndexedFieldSet(
            (
                IndexedField(name="person_ref", order=Order.ASCENDING),
                IndexedField(name="title", order=Order.ASCENDING),
                IndexedField(name="start_datetime", order=Order.ASCENDING),
            )
        ),
        IndexedFieldSet(
            (
                IndexedField(name="person_ref", order=Order.ASCENDING),
                IndexedField(name="title", order=Order.ASCENDING),
                IndexedField(name="start_datetime", order=Order.DESCENDING),
            )
        ),
        IndexedFieldSet(
            (
                IndexedField(name="person_ref", order=Order.ASCENDING),
                IndexedField(name="title", order=Order.ASCENDING),
                IndexedField(name="end_datetime", order=Order.ASCENDING),
            )
        ),
        IndexedFieldSet(
            (
                IndexedField(name="person_ref", order=Order.ASCENDING),
                IndexedField(name="title", order=Order.ASCENDING),
                IndexedField(name="end_datetime", order=Order.DESCENDING),
            )
        ),
        IndexedFieldSet(
            (
                IndexedField(name="end_datetime", order=Order.ASCENDING),
                IndexedField(name="seat_ref", order=Order.ASCENDING),
                IndexedField(name="start_datetime", order=Order.DESCENDING),
            )
        ),
    )


class Matter(Model):
    """
    A matter is a specific legislative document. A bill, resolution, initiative, etc.
    """

    id = fields.IDField()
    name = fields.TextField(required=True)
    matter_type = fields.TextField(required=True)
    title = fields.TextField(required=True)
    external_source_id = fields.TextField()

    class Meta:
        ignore_none_field = False

    @classmethod
    def Example(cls) -> Model:
        matter = cls()
        matter.name = "CB 119858"
        matter.matter_type = "Council Bill"
        matter.title = (
            "AN ORDINANCE relating to the financing of the West Seattle Bridge "
            "Immediate Response project; creating a fund for depositing proceeds of "
            "taxable limited tax general obligation bonds in 2021; authorizing the "
            "loan of funds in the amount of $50,000,000 from the Construction and "
            "Inspections Fund and $20,000,000 from the REET II Capital Projects Fund "
            "to the 2021 LTGO Taxable Bond Fund for early phases of work on the bridge "
            "repair and replacement project; amending Ordinance 126000, which adopted "
            "the 2020 Budget, including the 2020-2025 Capital Improvement Program "
            "(CIP); changing appropriations to the Seattle Department of "
            "Transportation; and revising project allocations and spending plans for "
            "certain projects in the 2020-2025 CIP."
        )
        return matter

    _PRIMARY_KEYS = ("name",)
    _INDEXES = ()


class MatterFile(Model):
    """
    A document related to a matter.

    This file is usually not stored in CDP infrastructure but a remote source.
    """

    id = fields.IDField()
    matter_ref = fields.ReferenceField(Matter, required=True, auto_load=False)
    name = fields.TextField(required=True)
    uri = fields.TextField(required=True, validator=validators.resource_exists)
    external_source_id = fields.TextField()

    class Meta:
        ignore_none_field = False

    def set_validator_kwargs(self, kwargs: Dict) -> None:
        field = fields.TextField(
            required=True, validator=validators.resource_exists, validator_kwargs=kwargs
        )

        field.contribute_to_model(MatterFile, "uri")

    @classmethod
    def Example(cls) -> Model:
        matter_file = cls()
        matter_file.matter_ref = Matter.Example()
        matter_file.name = "Amendment 3 (Sawant) - Sunset"
        matter_file.uri = (
            "http://legistar2.granicus.com/seattle/attachments/"
            "789a0c9f-dd9c-401b-aaf5-6c67c2a897b0.pdf"
        )
        return matter_file

    _PRIMARY_KEYS = ("matter_ref", "name", "uri")
    _INDEXES = (
        IndexedFieldSet(
            (
                IndexedField(name="matter_ref", order=Order.ASCENDING),
                IndexedField(name="name", order=Order.ASCENDING),
            )
        ),
    )


class MatterSponsor(Model):
    """
    A reference tying a specific person and a matter together.
    """

    id = fields.IDField()
    matter_ref = fields.ReferenceField(Matter, required=True, auto_load=False)
    person_ref = fields.ReferenceField(Person, required=True, auto_load=False)
    external_source_id = fields.TextField()

    class Meta:
        ignore_none_field = False

    @classmethod
    def Example(cls) -> Model:
        matter_sponsor = cls()
        matter_sponsor.matter_ref = Matter.Example()
        matter_sponsor.person_ref = Person.Example()
        return matter_sponsor

    _PRIMARY_KEYS = ("matter_ref", "person_ref")
    _INDEXES = (
        IndexedFieldSet(
            (
                IndexedField(name="person_ref", order=Order.ASCENDING),
                IndexedField(name="matter_ref", order=Order.ASCENDING),
            )
        ),
    )


class MinutesItem(Model):
    """
    An item referenced during a meeting.
    This can be a matter but it can be a presentation or budget file, etc.
    """

    id = fields.IDField()
    name = fields.TextField(required=True)
    description = fields.TextField()
    matter_ref = fields.ReferenceField(Matter, auto_load=False)  # Note optional.
    external_source_id = fields.TextField()

    class Meta:
        ignore_none_field = False

    @classmethod
    def Example(cls) -> Model:
        minutes_item = cls()
        minutes_item.name = "Inf 1656"
        minutes_item.description = (
            "Roadmap to defunding the Police and investing in community."
        )
        return minutes_item

    _PRIMARY_KEYS = ("name",)
    _INDEXES = ()


class Event(Model):
    """
    An event can be a normally scheduled meeting, a special event such as a press
    conference or election debate, and, can be upcoming or historical.
    """

    id = fields.IDField()
    body_ref = fields.ReferenceField(Body, required=True, auto_load=False)
    event_datetime = fields.DateTime(required=True)
    static_thumbnail_ref = fields.ReferenceField(File, auto_load=False)
    hover_thumbnail_ref = fields.ReferenceField(File, auto_load=False)
    agenda_uri = fields.TextField(validator=validators.resource_exists)
    minutes_uri = fields.TextField(validator=validators.resource_exists)
    external_source_id = fields.TextField()

    class Meta:
        ignore_none_field = False

    def set_validator_kwargs(self, kwargs: Dict) -> None:
        field = fields.TextField(
            validator=validators.resource_exists, validator_kwargs=kwargs
        )

        field.contribute_to_model(Event, "agenda_uri")
        field.contribute_to_model(Event, "minutes_uri")

    @classmethod
    def Example(cls) -> Model:
        event = cls()
        event.body_ref = Body.Example()
        event.event_datetime = datetime.utcnow()
        event.agenda_uri = (
            "http://legistar2.granicus.com/seattle/meetings/2019/11/"
            "4169_A_Select_Budget_Committee_19-11-01_Committee_Agenda.pdf"
        )
        event.minutes_uri = (
            "http://legistar2.granicus.com/seattle/meetings/2019/7/"
            "4041_M_Council_Briefing_19-07-22_Committee_Minutes.pdf"
        )
        return event

    _PRIMARY_KEYS = ("body_ref", "event_datetime")
    _INDEXES = (
        IndexedFieldSet(
            (
                IndexedField(name="body_ref", order=Order.ASCENDING),
                IndexedField(name="event_datetime", order=Order.ASCENDING),
            )
        ),
        IndexedFieldSet(
            (
                IndexedField(name="body_ref", order=Order.ASCENDING),
                IndexedField(name="event_datetime", order=Order.DESCENDING),
            )
        ),
    )


class Session(Model):
    """
    A session is a working period for an event.
    For example, An event could have a morning and afternoon session.
    """

    id = fields.IDField()
    event_ref = fields.ReferenceField(Event, required=True, auto_load=False)
    session_datetime = fields.DateTime(required=True)
    session_index = fields.NumberField(required=True)
    session_content_hash = fields.TextField(required=True)
    video_uri = fields.TextField(required=True, validator=validators.resource_exists)
    caption_uri = fields.TextField(validator=validators.resource_exists)
    external_source_id = fields.TextField()

    class Meta:
        ignore_none_field = False

    def set_validator_kwargs(self, kwargs: Dict) -> None:
        field = fields.TextField(
            required=True, validator=validators.resource_exists, validator_kwargs=kwargs
        )

        field.contribute_to_model(Session, "video_uri")

    @classmethod
    def Example(cls) -> Model:
        session = cls()
        session.event_ref = Event.Example()
        session.session_index = 0
        session.video_uri = (
            "https://video.seattle.gov/media/council/brief_072219_2011957V.mp4"
        )
        session.session_content_hash = (
            "05bd857af7f70bf51b6aac1144046973bf3325c9101a554bc27dc9607dbbd8f5"
        )
        return session

    _PRIMARY_KEYS = ("event_ref", "video_uri")
    _INDEXES = (
        IndexedFieldSet(
            (
                IndexedField(name="event_ref", order=Order.ASCENDING),
                IndexedField(name="session_index", order=Order.ASCENDING),
            )
        ),
    )


class Transcript(Model):
    """
    A transcript is a document per-session.
    """

    id = fields.IDField()
    session_ref = fields.ReferenceField(Session, required=True, auto_load=False)
    file_ref = fields.ReferenceField(File, required=True, auto_load=False)
    generator = fields.TextField(required=True)
    confidence = fields.NumberField(required=True)
    created = fields.DateTime(required=True)

    class Meta:
        ignore_none_field = False

    @classmethod
    def Example(cls) -> Model:
        transcript = cls()
        transcript.session_ref = Session.Example()
        transcript.file_ref = File.Example()
        transcript.generator = "FakeGen -- v0.1.0"
        transcript.confidence = 0.943
        transcript.created = datetime.utcnow()
        return transcript

    _PRIMARY_KEYS = ("session_ref", "file_ref")
    _INDEXES = (
        IndexedFieldSet(
            (
                IndexedField(name="session_ref", order=Order.ASCENDING),
                IndexedField(name="created", order=Order.DESCENDING),
            )
        ),
        IndexedFieldSet(
            (
                IndexedField(name="session_ref", order=Order.ASCENDING),
                IndexedField(name="confidence", order=Order.DESCENDING),
            )
        ),
    )


class EventMinutesItem(Model):
    """
    A reference tying a specific minutes item to a specific event.
    """

    id = fields.IDField()
    event_ref = fields.ReferenceField(Event, required=True, auto_load=False)
    minutes_item_ref = fields.ReferenceField(
        MinutesItem, required=True, auto_load=False
    )
    index = fields.NumberField(required=True)
    decision = fields.TextField(
        validator=validators.create_constant_value_validator(EventMinutesItemDecision)
    )
    external_source_id = fields.TextField()

    class Meta:
        ignore_none_field = False

    @classmethod
    def Example(cls) -> Model:
        emi = cls()
        emi.event_ref = Event.Example()
        emi.minutes_item_ref = MinutesItem.Example()
        emi.index = 0
        emi.decision = EventMinutesItemDecision.PASSED
        return emi

    _PRIMARY_KEYS = ("event_ref", "minutes_item_ref")
    _INDEXES = (
        IndexedFieldSet(
            (
                IndexedField(name="event_ref", order=Order.ASCENDING),
                IndexedField(name="index", order=Order.ASCENDING),
            )
        ),
        IndexedFieldSet(
            (
                IndexedField(name="event_ref", order=Order.ASCENDING),
                IndexedField(name="index", order=Order.DESCENDING),
            )
        ),
    )


class MatterStatus(Model):
    """
    A matter status is the status of a matter at any given time. Useful for tracking
    the timelines of matters. I.E. Return me a timeline of matter x.

    The same matter will have multiple matter statuses.
    1. MatterStatus of submitted
    2. MatterStatus of passed
    3. MatterStatus of signed
    4. etc.
    """

    id = fields.IDField()
    matter_ref = fields.ReferenceField(Matter, required=True, auto_load=False)
    # Optional because status can be updated out of event
    # i.e. Signed by Mayor
    event_minutes_item_ref = fields.ReferenceField(EventMinutesItem, auto_load=False)
    status = fields.TextField(
        required=True,
        validator=validators.create_constant_value_validator(MatterStatusDecision),
    )
    update_datetime = fields.DateTime(required=True)
    external_source_id = fields.TextField()

    class Meta:
        ignore_none_field = False

    @classmethod
    def Example(cls) -> Model:
        matter_status = cls()
        matter_status.matter_ref = Matter.Example()
        matter_status.status = MatterStatusDecision.ADOPTED
        matter_status.update_datetime = datetime.utcnow()
        return matter_status

    _PRIMARY_KEYS = ("matter_ref", "status", "update_datetime")
    _INDEXES = (
        IndexedFieldSet(
            (
                IndexedField(name="matter_ref", order=Order.ASCENDING),
                IndexedField(name="update_datetime", order=Order.ASCENDING),
            ),
        ),
        IndexedFieldSet(
            (
                IndexedField(name="matter_ref", order=Order.ASCENDING),
                IndexedField(name="update_datetime", order=Order.DESCENDING),
            ),
        ),
    )


class EventMinutesItemFile(Model):
    """
    Supporting files for an event minutes item.
    """

    id = fields.IDField()
    event_minutes_item_ref = fields.ReferenceField(
        EventMinutesItem, required=True, auto_load=False
    )
    name = fields.TextField(required=True)
    uri = fields.TextField(required=True, validator=validators.resource_exists)
    external_source_id = fields.TextField()

    class Meta:
        ignore_none_field = False

    def set_validator_kwargs(self, kwargs: Dict) -> None:
        field = fields.TextField(
            required=True, validator=validators.resource_exists, validator_kwargs=kwargs
        )

        field.contribute_to_model(EventMinutesItemFile, "uri")

    @classmethod
    def Example(cls) -> Model:
        emif = cls()
        emif.event_minutes_item_ref = EventMinutesItem.Example()
        emif.name = "Levy to Move Seattle Quartly Report"
        emif.uri = (
            "http://legistar2.granicus.com/seattle/attachments/"
            "ec6595cf-e2c3-449d-811b-047675d047df.pdf"
        )
        return emif

    _PRIMARY_KEYS = ("event_minutes_item_ref", "uri")
    _INDEXES = (
        IndexedFieldSet(
            (
                IndexedField(name="event_minutes_item_ref", order=Order.ASCENDING),
                IndexedField(name="name", order=Order.ASCENDING),
            )
        ),
    )


class Vote(Model):
    """
    A reference tying a specific person and an event minutes item together.
    """

    id = fields.IDField()
    matter_ref = fields.ReferenceField(Matter, required=True, auto_load=False)
    event_ref = fields.ReferenceField(Event, required=True, auto_load=False)
    event_minutes_item_ref = fields.ReferenceField(
        EventMinutesItem, required=True, auto_load=False
    )
    person_ref = fields.ReferenceField(Person, required=True, auto_load=False)
    decision = fields.TextField(
        required=True,
        validator=validators.create_constant_value_validator(VoteDecision),
    )
    in_majority = fields.BooleanField()
    external_source_id = fields.TextField()

    class Meta:
        ignore_none_field = False

    @classmethod
    def Example(cls) -> Model:
        vote = cls()
        vote.matter_ref = Matter.Example()
        vote.event_ref = Event.Example()
        vote.event_minutes_item_ref = EventMinutesItem.Example()
        vote.person_ref = Person.Example()
        vote.decision = VoteDecision.APPROVE
        vote.in_majority = True
        return vote

    _PRIMARY_KEYS = (
        "matter_ref",
        "event_ref",
        "event_minutes_item_ref",
        "person_ref",
        "decision",
    )
    _INDEXES = (
        IndexedFieldSet(
            (
                IndexedField(name="event_ref", order=Order.ASCENDING),
                IndexedField(name="person_ref", order=Order.ASCENDING),
            )
        ),
        IndexedFieldSet(
            (
                IndexedField(name="matter_ref", order=Order.ASCENDING),
                IndexedField(name="person_ref", order=Order.ASCENDING),
            )
        ),
        IndexedFieldSet(
            (
                IndexedField(name="person_ref", order=Order.ASCENDING),
                IndexedField(name="event_ref", order=Order.ASCENDING),
            )
        ),
        IndexedFieldSet(
            (
                IndexedField(name="person_ref", order=Order.ASCENDING),
                IndexedField(name="matter_ref", order=Order.ASCENDING),
            )
        ),
    )


class IndexedEventGram(Model):
    """
    An n-gram that has already been scored to create, when taken altogether,
    an event relevance index.
    """

    id = fields.IDField()
    event_ref = fields.ReferenceField(Event, required=True, auto_load=False)
    unstemmed_gram = fields.TextField(required=True)
    stemmed_gram = fields.TextField(required=True)
    context_span = fields.TextField(required=True)
    value = fields.NumberField(required=True)
    datetime_weighted_value = fields.NumberField(required=True)

    class Meta:
        ignore_none_field = False

    @classmethod
    def Example(cls) -> Model:
        ieg = cls()
        ieg.event_ref = Event.Example()
        ieg.unstemmed_gram = "housing"
        ieg.stemmed_gram = "hous"
        ieg.context_span = "We believe that housing should be affordable."
        ieg.value = 12.34
        ieg.datetime_weighted_value = 1.234
        return ieg

    _PRIMARY_KEYS = (
        "event_ref",
        "unstemmed_gram",
        "stemmed_gram",
    )
    _INDEXES = (
        IndexedFieldSet(
            (
                IndexedField(name="event_ref", order=Order.ASCENDING),
                IndexedField(name="value", order=Order.DESCENDING),
            ),
        ),
        IndexedFieldSet(
            (
                IndexedField(name="event_ref", order=Order.ASCENDING),
                IndexedField(name="datetime_weighted_value", order=Order.DESCENDING),
            ),
        ),
        IndexedFieldSet(
            (
                IndexedField(name="stemmed_gram", order=Order.ASCENDING),
                IndexedField(name="value", order=Order.DESCENDING),
            ),
        ),
        IndexedFieldSet(
            (
                IndexedField(name="stemmed_gram", order=Order.ASCENDING),
                IndexedField(name="datetime_weighted_value", order=Order.DESCENDING),
            ),
        ),
        IndexedFieldSet(
            (
                IndexedField(name="unstemmed_gram", order=Order.ASCENDING),
                IndexedField(name="value", order=Order.DESCENDING),
            ),
        ),
        IndexedFieldSet(
            (
                IndexedField(name="unstemmed_gram", order=Order.ASCENDING),
                IndexedField(name="datetime_weighted_value", order=Order.DESCENDING),
            ),
        ),
    )
