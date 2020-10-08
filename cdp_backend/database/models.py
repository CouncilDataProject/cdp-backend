#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any, NamedTuple
from abc import ABC, abstractmethod

###############################################################################


class Order:
    ASCENDING = "ASCENDING"
    DESCENDING = "DESCENDING"

class IndexedField(NamedTuple):
    name: str
    order: str

class Model(ABC):
    @classmethod
    @abstractmethod
    def example(cls):
        pass

    @staticmethod
    @abstractmethod
    def primary_keys():
        pass

    @staticmethod
    @abstractmethod
    def indexes():
        pass

###############################################################################

# TODO: look at quickle, https://jcristharif.com/quickle/


@dataclass
class Body(Model):
    """
    A body, also known as committee, is a subset of city council members that stands
    for a certain topic/purpose. An example would be the Seattle "Governance and
    Education" committee which consists of 6 of the 9 city council members. This can
    however include general categories such as "Debate", or "Press Conference", etc.
    """
    name: str
    body_id: Optional[str] = None
    tag: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: bool = False
    chair_person_id: Optional[str] = None
    external_source_id: Optional[Any] = None
    updated: Optional[datetime] = None
    created: Optional[datetime] = None

    @classmethod
    def example(cls):
        return cls(
            name="Full Council",
            description="All Council Members",
            is_active=True,
            chair_person_id="c6ba8397-114a-4492-b868-b97942003e62",
            external_source_id=121314,
        )

    @staticmethod
    def primary_keys():
        return ["name"]

    @staticmethod
    def indexes():
        return [
            IndexedField("name", Order.DESCENDING),
            IndexedField("start_date", Order.DESCENDING),
        ]
