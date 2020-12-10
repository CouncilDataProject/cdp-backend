#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass

###############################################################################


@dataclass
class Seat:
    """
    An electable office on the City Council. I.E. "Position 9".

    Notes
    -----
    The electoral_area and electoral_type will be updated if changed from prior values.
    The image will be uploaded or updated in the CDP file storage system.
    """

    name: str
    electoral_area: Optional[str] = None
    electoral_type: Optional[str] = None
    image_uri: Optional[str] = None
    external_source_id: Optional[str] = None


@dataclass
class Person:
    """
    Primarily the council members, this could technically include the mayor or city
    manager, or any other "normal" presenters and attendees of meetings.

    Notes
    -----
    If router_string is not provided, and the Person did not exist prior to ingestion,
    router_string will be generated from name.

    The email, phone, website will be updated if changed from prior values.
    The picture will be uploaded or updated in the CDP file storage system.

    If person is operating under new roles or new seat, new Role and Seat documents will
    be stored.
    """

    name: str
    is_active: bool = True
    router_string: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    picture_uri: Optional[str] = None
    seat: Optional[Seat] = None
    roles: Optional[List[Role]] = None
    external_source_id: Optional[str] = None


@dataclass
class Vote:
    """
    A reference tying a specific person and an event minutes item together.

    Notes
    -----
    The in_majority field stored in the database will be calculated from the provided
    list of votes.
    """

    person: Person
    decision: str
    external_source_id: Optional[str] = None


@dataclass
class SupportingFile:
    """
    A file related tied to a matter or minutes item.

    Notes
    -----
    This file is not stored in the CDP file storage system.
    """

    name: str
    uri: str
    external_source_id: Optional[str] = None


@dataclass
class Matter:
    """
    A matter is a specific legislative document. A bill, resolution, initiative, etc.
    """

    name: str
    matter_type: str
    title: str
    sponsors: Optional[List[Person]] = None
    external_source_id: Optional[str] = None


@dataclass
class MinutesItem:
    """
    An item referenced during a meeting.
    This can be a matter but it can be a presentation or budget file, etc.
    """

    name: str
    description: Optional[str] = None
    external_source_id: Optional[str] = None


@dataclass
class EventMinutesItem:
    """
    Details about a specific item during an event.

    Notes
    -----
    If index is not provided, the index will be set to the index of the item in the
    whole EventMinutesItem list on Event.

    If matter is not provided, the supporting_files will be stored as
    EventMinutesItemFile.
    If matter is provided, the supporting_files will be additionally be stored as
    MatterFile.
    """

    minutes_item: MinutesItem
    index: Optional[int] = None
    matter: Optional[Matter] = None
    supporting_files: Optional[List[SupportingFile]] = None
    decision: Optional[str] = None
    votes: Optional[List[Vote]] = None


@dataclass
class Session:
    """
    A session is a working period for an event.
    For example, an event could have a morning and afternoon session.

    Notes
    -----
    If session_index is not provided, the session_index will be set to the index of the
    item in the whole Session list on Event.
    """

    session_datetime: datetime
    video_uri: str
    session_index: Optional[int] = None
    caption_uri: Optional[str] = None
    external_source_id: Optional[str] = None


@dataclass
class Body:
    """
    A meeting body. This can be full council, a subcommittee, or "off-council" matters
    such as election debates.

    Notes
    -----
    If start_datetime is not provided, and the Body did not exist prior to ingestion,
    current datetime.utcnow will be used as start_datetime during storage.
    """

    name: str
    is_active: bool = True
    start_datetime: Optional[datetime] = None
    description: Optional[str] = None
    end_datetime: Optional[datetime] = None
    external_source_id: Optional[str] = None


@dataclass
class Role:
    """
    A role is a person's job for a period of time in the city council. A person can
    (and should) have multiple roles. For example: a person has two terms as city
    council member for district four then a term as city council member for a citywide
    seat. Roles can also be tied to committee chairs. For example: a council member
    spends a term on the transportation committee and then spends a term on the finance
    committee.

    Notes
    -----
    If start_datetime is not provided, and the Role did not exist prior to ingestion,
    current datetime.utcnow will be used as start_datetime during storage.
    """

    title: str
    body: Optional[Body] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    external_source_id: Optional[str] = None


@dataclass
class EventIngestionModel:
    """
    An event can be a normally scheduled meeting, a special event such as a press
    conference or election debate, and, can be upcoming or historical.

    Notes
    -----
    If static_thumbnail_uri and/or hover_thumbnail_uri is not provided,
    it will be generated during pipeline processing.

    The earliest session_datetime will be used for the overall event_datetime.
    """

    body: Body
    sessions: List[Session]
    event_minutes_items: Optional[List[EventMinutesItem]] = None
    agenda_uri: Optional[str] = None
    minutes_uri: Optional[str] = None
    static_thumbnail_uri: Optional[str] = None
    hover_thumbnail_uri: Optional[str] = None
    external_source_id: Optional[str] = None


###############################################################################


EXAMPLE_MINIMAL_EVENT = EventIngestionModel(
    body=Body(name="Full Council"),
    sessions=[
        Session(
            session_datetime=datetime.utcnow(),
            video_uri="https://youtu.be/dQw4w9WgXcQ",
        ),
    ],
)


EXAMPLE_FILLED_EVENT = EventIngestionModel(
    body=Body(name="Full Council"),
    sessions=[
        Session(
            session_datetime=datetime.utcnow(),
            video_uri="https://youtu.be/dQw4w9WgXcQ",
        ),
    ],
    event_minutes_items=[
        EventMinutesItem(
            minutes_item=MinutesItem(name="Inf 1656"),
        ),
        EventMinutesItem(
            minutes_item=MinutesItem(name="CB 119858"),
            matter=Matter(
                name="CB 119858",
                matter_type="Council Bill",
                title=(
                    "AN ORDINANCE relating to the financing of the West Seattle Bridge"
                ),
                sponsors=[
                    Person(
                        name="M. Lorena González",
                        seat=Seat(name="Position 9"),
                        roles=[
                            Role(title="Council President"),
                            Role(
                                title="Chair",
                                body=Body(name="Governance and Education"),
                            ),
                        ],
                    ),
                    Person(
                        name="Teresa Mosqueda",
                        seat=Seat(name="Position 8"),
                        roles=[
                            Role(
                                title="Chair",
                                body=Body(name="Finance and Housing"),
                            ),
                            Role(
                                title="Vice Chair",
                                body=Body(name="Governance and Education"),
                            ),
                        ],
                    ),
                ],
            ),
            supporting_files=[
                SupportingFile(
                    name="Amendment 3",
                    uri=(
                        "http://legistar2.granicus.com/seattle/attachments/"
                        "789a0c9f-dd9c-401b-aaf5-6c67c2a897b0.pdf"
                    ),
                ),
            ],
            decision="Passed",
            votes=[
                Vote(
                    person=Person(
                        name="M. Lorena González",
                        seat=Seat(name="Position 9"),
                        roles=[
                            Role(title="Council President"),
                            Role(
                                title="Chair",
                                body=Body(name="Governance and Education"),
                            ),
                        ],
                    ),
                    decision="Approve",
                ),
                Vote(
                    person=Person(
                        name="Teresa Mosqueda",
                        seat=Seat(name="Position 8"),
                        roles=[
                            Role(
                                title="Chair",
                                body=Body(name="Finance and Housing"),
                            ),
                            Role(
                                title="Vice Chair",
                                body=Body(name="Governance and Education"),
                            ),
                        ],
                    ),
                    decision="Approve",
                ),
                Vote(
                    person=Person(
                        name="Andrew Lewis",
                        seat=Seat(name="District 7"),
                        roles=[
                            Role(
                                title="Vice Chair",
                                body=Body(name="Community Economic Development"),
                            ),
                        ],
                    ),
                    decision="Approve",
                ),
                Vote(
                    person=Person(
                        name="Alex Pedersen",
                        seat=Seat(name="District 4"),
                        roles=[
                            Role(
                                title="Chair",
                                body=Body("Transportation and Utilities"),
                            ),
                        ],
                    ),
                    decision="Reject",
                ),
            ],
        ),
    ],
)
