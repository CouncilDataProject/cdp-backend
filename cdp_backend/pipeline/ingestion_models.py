#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
from typing import NamedTuple, Optional, List


class File(NamedTuple):
    uri: str
    name: str
    description: Optional[str]
    media_type: Optional[str]


class Matter(NamedTuple):
    name: str
    matter_type: str
    title: str
    external_source_id: Optional[str]


class Person(NamedTuple):
    name: str
    router_string: Optional[str]
    email: Optional[str]
    phone: Optional[int]
    website: Optional[str]
    picture_ref: Optional[File]
    is_active: Optional[bool]
    external_source_id: Optional[str]


class Vote(NamedTuple):
    matter_ref: Matter
    person_ref: Person
    decision: str
    in_majority: bool
    external_source_id: Optional[str]


class SessionData(NamedTuple):
    session_datetime: datetime
    session_index: int
    video_uri: str
    caption_uri: Optional[str]
    external_source_id: Optional[str]


class MinutesItem(NamedTuple):
    name: str
    description: str
    matter_ref: Optional[Matter]
    external_source_id: Optional[str]


class EventMinutesItem(NamedTuple):
    minutes_item_ref: MinutesItem  # top down
    event_minutes_item_index: int
    decision: str
    external_source_id: Optional[str]
    vote: Vote


class Body(NamedTuple):
    name: str
    tag: Optional[str]
    description: Optional[str]
    start_datetime: datetime
    end_datetime: Optional[datetime]
    is_active: Optional[bool]
    external_source_id: Optional[str]


class EventData(NamedTuple):
    body_ref: Body
    event_datetime: datetime
    sessions: List[SessionData]
    external_source_id: Optional[str]
    event_minutes_items: Optional[List[EventMinutesItem]]  # top down
