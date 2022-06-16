#!/usr/bin/env python
# -*- coding: utf-8 -*-


class Order:
    ASCENDING = "ASCENDING"
    DESCENDING = "DESCENDING"


class EventMinutesItemDecision:
    PASSED = "Passed"
    FAILED = "Failed"


class VoteDecision:
    """
    Abstain and Absent can mean many things.
    It depends on each municipality what each legally dictates.

    See here:
    https://mrsc.org/Home/Stay-Informed/MRSC-Insight/April-2013/How-Are-Abstentions-Handled-When-Counting-Votes.aspx

    You may see "Non-Voting" reported as `(NV)` from Legistar for
    example.
    """

    APPROVE = "Approve"
    REJECT = "Reject"
    ABSTAIN_NON_VOTING = "Abstain (Non-Voting)"
    ABSTAIN_APPROVE = "Abstain (Approve)"
    ABSTAIN_REJECT = "Abstain (Reject)"
    ABSENT_NON_VOTING = "Absent (Non-Voting)"
    ABSENT_APPROVE = "Absent (Approve)"
    ABSENT_REJECT = "Absent (Reject)"


class MatterStatusDecision:
    ADOPTED = "Adopted"
    REJECTED = "Rejected"
    IN_PROGRESS = "In Progress"


class RoleTitle:
    COUNCILMEMBER = "Councilmember"
    COUNCILPRESIDENT = "Council President"
    CHAIR = "Chair"
    VICE_CHAIR = "Vice Chair"
    ALTERNATE = "Alternate"
    MEMBER = "Member"
    SUPERVISOR = "Supervisor"
