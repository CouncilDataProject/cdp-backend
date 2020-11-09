#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import pulumi

from cdp_backend.infrastructure import CDPStack

###############################################################################


# Create the various mocks.
class CDPStackMocks(pulumi.runtime.Mocks):
    def call(self, token, args, provider):
        return {}

    def new_resource(self, type_, name, inputs, provider, id_):
        if type_ == "gcp:appengine/application:Application":
            state = {
                "app_id": f"{name}.fake-appspot.io",
                "default_bucket": f"gcs://{name}",
            }
            return [name, dict(inputs, **state)]

        return ["", {}]


pulumi.runtime.set_mocks(CDPStackMocks())

###############################################################################


class InfrastructureTests(unittest.TestCase):
    @pulumi.runtime.test
    def test_basic_run(self):
        gcp_project_id = "mocked-testing-stack"

        # Write output checks
        def check_firestore_app_id(args):
            app_id = args
            assert app_id == f"{gcp_project_id}.fake-appspot.io"

        def check_firestore_default_bucket(args):
            default_bucket = args
            assert default_bucket == f"gcs://{gcp_project_id}"

        # Init mocked stack
        stack = CDPStack("mocked-testing-stack")

        # Check outputs
        pulumi.Output.all(stack.firestore_app.app_id).apply(check_firestore_app_id)
        pulumi.Output.all(stack.firestore_app.default_bucket).apply(
            check_firestore_default_bucket
        )
