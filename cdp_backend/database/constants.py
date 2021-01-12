#!/usr/bin/env python
# -*- coding: utf-8 -*-


class Order:
    ASCENDING = "ASCENDING"
    DESCENDING = "DESCENDING"


class EventMinutesItemDecision:
    PASSED = "Passed"
    FAILED = "Failed"


class VoteDecision:
    APPROVE = "Approve"
    REJECT = "Reject"
    ABSTAIN = "Abstain"


class MatterStatusDecision:
    ADOPTED = "Adopted"
    REJECTED = "Rejected"
    IN_PROGRESS = "In Progress"
