#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime

from fireo.models import Model
from fireo import fields

from . import validators
from ..utils import file_utils
from .types import IndexedField, IndexedFieldSet, Order

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

    name = fields.TextField(required=True)
    router_string = fields.TextField(
        required=True, validator=validators.router_string_is_valid
    )
    email = fields.TextField(validator=validators.email_is_valid)
    phone = fields.NumberField()
    website = fields.TextField(validator=validators.resource_exists)
    picture_ref = fields.ReferenceField(File)
    is_active = fields.BooleanField(required=True)
    external_source_id = fields.TextField()

    @classmethod
    def Example(cls) -> Model:
        person = cls()
        person.name = "M. Lorena González"
        person.router_string = "lorena-gonzalez"
        person.is_active = True
        return person

    _PRIMARY_KEYS = ("name",)
    _INDEXES = ()


class Body(Model):
    """
    A meeting body. This can be full council, a subcommittee, or "off-council" matters
    such as election debates.
    """

    name = fields.TextField(required=True)
    description = fields.TextField()
    start_datetime = fields.DateTime(required=True)
    end_datetime = fields.DateTime()
    is_active = fields.BooleanField(required=True)
    external_source_id = fields.TextField()

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

    name = fields.TextField(required=True)
    electoral_area = fields.TextField()
    electoral_type = fields.TextField()
    image_ref = fields.ReferenceField(File)
    external_source_id = fields.TextField()

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

    title = fields.TextField(required=True)
    person_ref = fields.ReferenceField(Person, required=True)
    body_ref = fields.ReferenceField(Body)
    seat_ref = fields.ReferenceField(Seat, required=True)
    start_datetime = fields.DateTime(required=True)
    end_datetime = fields.DateTime()
    external_source_id = fields.TextField()

    @classmethod
    def Example(cls) -> Model:
        role = cls()
        role.title = "Council President"
        role.person_ref = Person.Example()
        role.body_ref = Body.Example()
        role.seat_ref = Seat.Example()
        role.start_datetime = datetime.utcnow()
        return role

    _PRIMARY_KEYS = ("title", "person_ref", "body_ref", "seat_ref")
    _INDEXES = ()


class Matter(Model):
    """
    A matter is a specific legislative document. A bill, resolution, initiative, etc.
    """

    name = fields.TextField(required=True)
    matter_type = fields.TextField(required=True)
    title = fields.TextField(required=True)
    external_source_id = fields.TextField()

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

    matter_ref = fields.ReferenceField(Matter, required=True)
    status = fields.TextField(required=True)
    update_datetime = fields.DateTime(required=True)
    external_source_id = fields.TextField()

    @classmethod
    def Example(cls) -> Model:
        matter_status = cls()
        matter_status.matter_ref = Matter.Example()
        matter_status.status = "Passed"
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


class MatterFile(Model):
    """
    A document related to a matter.

    This file is usually not stored in CDP infrastructure but a remote source.
    """

    matter_ref = fields.ReferenceField(Matter, required=True)
    name = fields.TextField(required=True)
    uri = fields.TextField(required=True, validator=validators.resource_exists)
    external_source_id = fields.TextField()

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

    matter_ref = fields.ReferenceField(Matter, required=True)
    person_ref = fields.ReferenceField(Person, required=True)
    external_source_id = fields.TextField()

    @classmethod
    def Example(cls) -> Model:
        matter_sponsor = cls()
        matter_sponsor.matter_ref = Matter.Example()
        matter_sponsor.person_ref = Person.Example()
        return matter_sponsor

    _PRIMARY_KEYS = ("matter_ref", "person_ref")
    _INDEXES = ()


class MinutesItem(Model):
    """
    An item referenced during a meeting.
    This can be a matter but it can be a presentation or budget file, etc.
    """

    name = fields.TextField(required=True)
    description = fields.TextField()
    matter_ref = fields.ReferenceField(Matter)  # Note optional.
    external_source_id = fields.TextField()

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

    body_ref = fields.ReferenceField(Body, required=True)
    event_datetime = fields.DateTime(required=True)
    static_thumbnail_ref = fields.ReferenceField(File)
    hover_thumbnail_ref = fields.ReferenceField(File)
    agenda_uri = fields.TextField(validator=validators.resource_exists)
    minutes_uri = fields.TextField(validator=validators.resource_exists)
    external_source_id = fields.TextField()

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

    event_ref = fields.ReferenceField(Event, required=True)
    session_datetime = fields.DateTime(required=True)
    session_index = fields.NumberField(required=True)
    video_uri = fields.TextField(required=True, validator=validators.resource_exists)
    caption_uri = fields.TextField(validator=validators.resource_exists)
    external_source_id = fields.TextField()

    @classmethod
    def Example(cls) -> Model:
        session = cls()
        session.event_ref = Event.Example()
        session.session_index = 0
        session.video_uri = (
            "https://video.seattle.gov/media/council/brief_072219_2011957V.mp4"
        )
        return session

    _PRIMARY_KEYS = ("event_ref", "video_uri")
    _INDEXES = ()


class Transcript(Model):
    """
    A transcript is a document per-session.
    """

    session_ref = fields.ReferenceField(Session, required=True)
    file_ref = fields.ReferenceField(File, required=True)
    confidence = fields.NumberField(required=True)
    created = fields.DateTime(required=True)

    @classmethod
    def Example(cls) -> Model:
        transcript = cls()
        transcript.session_ref = Session.Example()
        transcript.file_ref = File.Example()
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

    event_ref = fields.ReferenceField(Event, required=True)
    minutes_item_ref = fields.ReferenceField(MinutesItem, required=True)
    index = fields.NumberField(required=True)
    decision = fields.TextField()
    external_source_id = fields.TextField()

    @classmethod
    def Example(cls) -> Model:
        emi = cls()
        emi.event_ref = Event.Example()
        emi.minutes_item_ref = MinutesItem.Example()
        emi.index = 0
        emi.decision = "Passed"
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


class EventMinutesItemFile(Model):
    """
    Supporting files for an event minutes item.
    """

    event_minutes_item_ref = fields.ReferenceField(EventMinutesItem, required=True)
    name = fields.TextField(required=True)
    uri = fields.TextField(required=True, validator=validators.resource_exists)
    external_source_id = fields.TextField()

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

    matter_ref = fields.ReferenceField(Matter, required=True)
    event_ref = fields.ReferenceField(Event, required=True)
    event_minutes_item_ref = fields.ReferenceField(EventMinutesItem, required=True)
    person_ref = fields.ReferenceField(Person, required=True)
    decision = fields.TextField(required=True)
    in_majority = fields.BooleanField(required=True)
    external_source_id = fields.TextField()

    @classmethod
    def Example(cls) -> Model:
        vote = cls()
        vote.matter_ref = Matter.Example()
        vote.event_ref = Event.Example()
        vote.event_minutes_item_ref = EventMinutesItem.Example()
        vote.person_ref = Person.Example()
        vote.decision = "Approve"
        vote.in_majority = True
        return vote

    _PRIMARY_KEYS = (
        "matter_ref",
        "event_ref",
        "event_minutes_item_ref",
        "person_ref",
        "decision",
    )
    _INDEXES = ()
