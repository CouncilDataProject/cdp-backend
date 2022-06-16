#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from typing import Any, Dict, List, Optional, Tuple

import pulumi

###############################################################################


# Create the various mocks.
class CDPStackMocks(pulumi.runtime.Mocks):
    def call(
        self, args: pulumi.runtime.MockCallArgs
    ) -> Tuple[Dict[Any, Any], Optional[List[Tuple[str, str]]]]:
        return {}, None

    def new_resource(
        self, args: pulumi.runtime.MockResourceArgs
    ) -> Tuple[Optional[str], Dict[Any, Any]]:
        return (args.name + "_id", args.inputs)


pulumi.runtime.set_mocks(CDPStackMocks())

from cdp_backend.infrastructure import CDPStack

###############################################################################


class InfrastructureTests(unittest.TestCase):
    @pulumi.runtime.test
    def test_basic_run(self) -> None:
        gcp_project_id = "mocked-testing-stack"

        # Write output checks
        def check_firestore_app_id(args: List[Any]) -> None:
            app_id = args
            assert app_id == f"{gcp_project_id}.fake-appspot.io"

        def check_firestore_default_bucket(args: List[Any]) -> None:
            default_bucket = args
            assert default_bucket == f"gcs://{gcp_project_id}"

        # Init mocked stack
        stack = CDPStack("mocked-testing-stack")

        # Check outputs
        pulumi.Output.all(stack.firestore_app.app_id).apply(check_firestore_app_id)
        pulumi.Output.all(stack.firestore_app.default_bucket).apply(
            check_firestore_default_bucket
        )
