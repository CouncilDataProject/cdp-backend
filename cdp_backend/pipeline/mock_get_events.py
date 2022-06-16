#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
from bisect import bisect_left
from datetime import datetime, timedelta
from typing import Any, List

from ..database.constants import (
    EventMinutesItemDecision,
    MatterStatusDecision,
    RoleTitle,
    VoteDecision,
)
from ..utils.constants_utils import get_all_class_attr_values
from .ingestion_models import (
    EXAMPLE_FILLED_EVENT,
    EXAMPLE_MINIMAL_EVENT,
    Body,
    EventIngestionModel,
    EventMinutesItem,
    Matter,
    MinutesItem,
    Person,
    Role,
    Seat,
    Session,
    SupportingFile,
    Vote,
)
from .pipeline_config import EventGatherPipelineConfig

###############################################################################


NUM_COUNCIL_SEATS = 10
RAND_BODY_RANGE = (1, 100)
RAND_EVENT_MINUTES_ITEMS_RANGE = (5, 10)
RAND_MATTER_RANGE = (1, 1000)

ALL_EVENT_MINUTES_ITEM_DECISIONS = get_all_class_attr_values(EventMinutesItemDecision)
PASSING_VOTE_DECISIONS = [VoteDecision.APPROVE]
FAILING_VOTE_DECISIONS = [VoteDecision.ABSTAIN_REJECT, VoteDecision.REJECT]

DUMMY_FILE_URI = (
    "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
)
PERSON_PICTURE_URI = (
    "https://councildataproject.github.io/imgs/public-speaker-light-purple.svg"
)
SEAT_URI = "https://councildataproject.github.io/imgs/seattle.jpg"

SESSIONS = [
    (
        "https://video.seattle.gov/media/council/council_010421_2022101V.mp4",
        "https://www.seattlechannel.org/documents/seattlechannel/closedcaption/2021/council_010421_2022101.vtt",  # noqa
    ),
    (
        "https://video.seattle.gov/media/council/council_113020_2022091V.mp4",
        "https://www.seattlechannel.org/documents/seattlechannel/closedcaption/2020/council_113020_2022091.vtt",  # noqa
    ),
    (
        "https://video.seattle.gov/media/council/council_112320_2022089V.mp4",
        "https://www.seattlechannel.org/documents/seattlechannel/closedcaption/2020/brief_112320_2012089.vtt",  # noqa
    ),
    (
        "https://video.seattle.gov/media/council/council_110920_2022085V.mp4",
        "https://www.seattlechannel.org/documents/seattlechannel/closedcaption/2020/council_110920_2022085.vtt",  # noqa
    ),
    ("https://video.seattle.gov/media/council/council_101220_2022077V.mp4", None),
]


def _get_example_person(seat_num: int) -> Person:
    """
    Create a fake example person
    """
    # Create a list of roles
    roles = [
        Role(title=RoleTitle.COUNCILMEMBER, body=Body(name="Example Committee")),
        Role(title=RoleTitle.CHAIR, body=Body(name=f"Example Committee {seat_num}")),
    ]

    # Add Council President role for seat position 1
    if seat_num == 1:
        roles.append(
            Role(title=RoleTitle.COUNCILPRESIDENT, body=Body(name="Example Committee"))
        )

    # Get the seat electoral type num
    seat_electoral_type = 1 if seat_num <= NUM_COUNCIL_SEATS // 2 else 2
    return Person(
        name=f"Example Person {seat_num}",
        email="person@example.com",
        phone="123-456-7890",
        website="www.example.com",
        picture_uri=PERSON_PICTURE_URI,
        seat=Seat(
            name=f"Example Seat Position {seat_num}",
            electoral_area=f"Example Electoral Area {seat_num}",
            electoral_type=f"Example Electoral Type {seat_electoral_type}",
            image_uri=SEAT_URI,
            roles=roles,
        ),
    )


def _get_example_event() -> EventIngestionModel:
    """
    Create a fake example event data
    """
    # Create a body for the event
    body = Body(
        name=f"Example Committee {random.randint(*RAND_BODY_RANGE)}",
        description="Example Description",
    )

    # Create sessions for the event
    sessions = [
        Session(
            session_datetime=datetime.utcnow() + (i * timedelta(hours=3)),
            session_index=i,
            video_uri=session[0],
            caption_uri=session[1],
        )
        for i, session in enumerate(random.sample(SESSIONS, random.randint(1, 3)))
    ]

    # Get a number of event minutes items for the event
    num_event_minutes_items = random.randint(*RAND_EVENT_MINUTES_ITEMS_RANGE)

    # Get the decision for each event minutes item
    event_minutes_item_decisions = random.choices(
        ALL_EVENT_MINUTES_ITEM_DECISIONS, k=num_event_minutes_items
    )

    # Get the majority number of votes for each event minutes item
    vote_majority_nums = random.choices(
        range(NUM_COUNCIL_SEATS // 2 + 1, NUM_COUNCIL_SEATS + 1),
        k=num_event_minutes_items,
    )

    # Get the vote decisions for each event minutes item
    vote_decisions = [
        [
            *random.choices(
                PASSING_VOTE_DECISIONS
                if event_minutes_item_decisions[i] == EventMinutesItemDecision.PASSED
                else FAILING_VOTE_DECISIONS,
                k=vote_majority_nums[i],
            ),
            *random.choices(
                FAILING_VOTE_DECISIONS
                if event_minutes_item_decisions[i] == EventMinutesItemDecision.PASSED
                else PASSING_VOTE_DECISIONS,
                k=NUM_COUNCIL_SEATS - vote_majority_nums[i],
            ),
        ]
        for i in range(num_event_minutes_items)
    ]

    # Get a matter number for each event minutes item
    matter_nums = random.sample(
        range(RAND_MATTER_RANGE[0], RAND_MATTER_RANGE[1] + 1),
        num_event_minutes_items,
    )

    # Bin/discretize matter num.
    # The bin num for each matter are used to
    # determine the matter type and sponsor of the matter
    bins = range(0, RAND_MATTER_RANGE[1], RAND_MATTER_RANGE[1] // NUM_COUNCIL_SEATS)
    bin_nums = [bisect_left(bins, matter_num) for matter_num in matter_nums]

    # Create a list of event minutes item for the event
    event_minutes_items = [
        EventMinutesItem(
            minutes_item=MinutesItem(
                name=f"Example Minutes Item {matter_nums[i]}",
                description="Example Description",
            ),
            matter=Matter(
                name=f"Example Matter {matter_nums[i]}",
                matter_type=f"Example Matter Type {bin_nums[i]}",
                title="Example Matter Title",
                result_status=MatterStatusDecision.IN_PROGRESS,
                sponsors=[_get_example_person(bin_nums[i])],
            ),
            supporting_files=[
                SupportingFile(
                    name=f"Example Supporting File Name {file_num}",
                    uri=DUMMY_FILE_URI,
                )
                for file_num in range(1, random.randint(1, 5) + 1)
            ],
            decision=event_minutes_item_decisions[i],
            votes=[
                Vote(
                    person=_get_example_person(seat_num),
                    decision=vote_decisions[i][seat_num - 1],
                )
                for seat_num in range(1, NUM_COUNCIL_SEATS + 1)
            ],
        )
        for i in range(num_event_minutes_items)
    ]

    # Insert a non-matter event minutes item
    event_minutes_items.insert(
        0,
        EventMinutesItem(
            minutes_item=MinutesItem(
                name="Approval of Agenda", description="Example Description"
            )
        ),
    )

    return EventIngestionModel(
        body=body,
        sessions=sessions,
        event_minutes_items=event_minutes_items,
        agenda_uri=DUMMY_FILE_URI,
        minutes_uri=DUMMY_FILE_URI,
    )


def get_events(**kwargs: Any) -> List[EventIngestionModel]:
    """
    A mock get_events function that will generate entirely random events
    based off a set of permutation settings.

    Useful when running a pipeline test against a dev infrastructure.

    Also imported and used in the example repo and integration tests.
    """
    return [_get_example_event()]


RANDOM_FLOW_CONFIG = EventGatherPipelineConfig(
    google_credentials_file="",
    get_events_function_path="cdp_backend.pipeline.mock_get_events.get_events",
    gcs_bucket_name="",
)
RANDOM_FLOW_CONFIG._validated_gcs_bucket_name = ""


def min_get_events(**kwargs: Any) -> List[EventIngestionModel]:
    event = EXAMPLE_MINIMAL_EVENT
    event.sessions[0].session_datetime = datetime(2019, 4, 13)
    return [event]


MINIMAL_FLOW_CONFIG = EventGatherPipelineConfig(
    google_credentials_file="",
    get_events_function_path="cdp_backend.pipeline.mock_get_events.min_get_events",
    gcs_bucket_name="",
)
MINIMAL_FLOW_CONFIG._validated_gcs_bucket_name = ""


def filled_get_events(**kwargs: Any) -> List[EventIngestionModel]:
    event = EXAMPLE_FILLED_EVENT
    return [event]


FILLED_FLOW_CONFIG = EventGatherPipelineConfig(
    google_credentials_file="",
    get_events_function_path="cdp_backend.pipeline.mock_get_events.filled_get_events",
    gcs_bucket_name="",
)
FILLED_FLOW_CONFIG._validated_gcs_bucket_name = ""


def many_get_events(**kwargs: Any) -> List[EventIngestionModel]:
    event = EXAMPLE_MINIMAL_EVENT
    return [event] * 4


MANY_FLOW_CONFIG = EventGatherPipelineConfig(
    google_credentials_file="",
    get_events_function_path="cdp_backend.pipeline.mock_get_events.many_get_events",
    gcs_bucket_name="",
)
MANY_FLOW_CONFIG._validated_gcs_bucket_name = ""
