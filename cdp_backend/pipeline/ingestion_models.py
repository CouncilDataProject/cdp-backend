#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class File:
    """
    Parameters
    ----------
    uri: str
    name: str
    description: Optional[str]
    media_type: Optional[str]
    """

    uri: str
    name: str
    description: Optional[str] = None
    media_type: Optional[str] = None

    @classmethod
    def Example(cls) -> File:
        uri = "gs://cdp-example/central-staff-memo.pdf"
        name = "Central Staff Memo"
        return cls(uri, name)


@dataclass
class Matter:
    """
    Parameters
    ----------
    name: str
    matter_type: str
    title: str
    external_source_id: Optional[str]
    """

    name: str
    matter_type: str
    title: str
    external_source_id: Optional[str] = None

    @classmethod
    def Example(cls) -> Matter:
        name = "CB 119858"
        matter_type = "Council Bill"
        title = "A matter title"
        return cls(name, matter_type, title)


@dataclass
class Person:
    """
    Parameters
    ----------
    name: str
    router_string: Optional[str]
    email: Optional[str]
    phone: Optional[int]
    website: Optional[str]
    picture_ref: Optional[File]
    is_active: Optional[bool]
    external_source_id: Optional[str]
    """

    name: str
    router_string: Optional[str] = None
    is_active: Optional[bool] = None
    email: Optional[str] = None
    phone: Optional[int] = None
    website: Optional[str] = None
    picture_ref: Optional[File] = None
    external_source_id: Optional[str] = None

    @classmethod
    def Example(cls) -> Person:
        name = "M. Lorena González"
        router_string = "lorena-gonzalez"
        is_active = True
        return cls(name, router_string, is_active)


@dataclass
class Vote:
    """
    Parameters
    ----------
    matter_ref: Matter
    person_ref: Person
    decision: str
    in_majority: bool
    external_source_id: Optional[str]
    """

    matter_ref: Matter
    person_ref: Person
    decision: str
    in_majority: bool
    external_source_id: Optional[str] = None

    @classmethod
    def Example(cls) -> Vote:
        matter_ref = Matter.Example()
        person_ref = Person.Example()
        decision = "Approve"
        in_majority = True
        return cls(matter_ref, person_ref, decision, in_majority)


@dataclass
class SessionData:
    """
    Parameters
    ----------
    session_datetime: datetime
    session_index: int
    video_uri: str
    caption_uri: Optional[str]
    external_source_id: Optional[str]
    """

    session_datetime: datetime
    session_index: int
    video_uri: str
    caption_uri: Optional[str] = None
    external_source_id: Optional[str] = None

    @classmethod
    def Example(cls) -> SessionData:
        session_datetime = datetime.utcnow()
        session_index = 0
        video_uri = "https://video.seattle.gov/media/council/brief_072219_2011957V.mp4"
        return cls(session_datetime, session_index, video_uri)


@dataclass
class MinutesItem:
    """
    Parameters
    ----------
    name: str
    description: str
    matter_ref: Optional[Matter]
    external_source_id: Optional[str]
    """

    name: str
    description: str
    matter_ref: Optional[Matter] = None
    external_source_id: Optional[str] = None

    @classmethod
    def Example(cls) -> MinutesItem:
        name = "Inf 1656"
        description = "Roadmap to defunding the Police and investing in community."
        matter_ref = Matter.Example()
        return cls(name, description, matter_ref)


@dataclass
class EventMinutesItem:
    """
    Parameters
    ----------
    minutes_item_ref: MinutesItem
    event_minutes_item_index: int
    decision: str
    external_source_id: Optional[str]
    vote: Vote
    """

    minutes_item_ref: MinutesItem  # top down
    event_minutes_item_index: int
    decision: str
    vote: Vote
    external_source_id: Optional[str] = None

    @classmethod
    def Example(cls) -> EventMinutesItem:
        minutes_item_ref = MinutesItem.Example()
        event_minutes_item_index = 0
        decision = "Approved"
        vote = Vote.Example()
        return cls(minutes_item_ref, event_minutes_item_index, decision, vote)


@dataclass
class Body:
    """
    Parameters
    ----------
    name: str
    start_datetime: datetime
    tag: Optional[str]
    description: Optional[str]
    end_datetime: Optional[datetime]
    is_active: Optional[bool]
    external_source_id: Optional[str]
    """

    name: str
    start_datetime: datetime
    is_active: Optional[bool] = None
    tag: Optional[str] = None
    description: Optional[str] = None
    end_datetime: Optional[datetime] = None
    external_source_id: Optional[str] = None

    @classmethod
    def Example(cls) -> Body:
        name = "Full Council"
        is_active = True
        start_datetime = datetime.utcnow()
        return cls(name, start_datetime, is_active)


@dataclass
class EventData:
    """
    Parameters
    ----------
    body_ref: Body
    event_datetime: datetime
    sessions: List[SessionData]
    external_source_id: Optional[str]
    event_minutes_items: Optional[List[EventMinutesItem]]
    """

    body_ref: Body
    event_datetime: datetime
    sessions: List[SessionData]
    external_source_id: Optional[str] = None
    event_minutes_items: Optional[List[EventMinutesItem]] = None  # top down

    @classmethod
    def Example(cls) -> EventData:
        body_ref = Body.Example()
        event_datetime = datetime.utcnow()
        sessions = [SessionData.Example(), SessionData.Example()]
        return cls(body_ref, event_datetime, sessions)
