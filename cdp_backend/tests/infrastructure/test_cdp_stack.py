#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import unittest
from typing import Any, Dict, List, Optional, Tuple

import pulumi
import pytest

###############################################################################


# Create the various mocks.
class CDPStackMocks(pulumi.runtime.Mocks):
    def call(self, token: str, args: Any, provider: Optional[str]) -> Dict:
        return {}

    def new_resource(
        self,
        type_: str,
        name: str,
        inputs: Any,
        provider: Optional[str],
        id_: Optional[str],
    ) -> Tuple[str, Dict[Any, Any]]:
        if type_ == "gcp:appengine/application:Application":
            state = {
                "app_id": f"{name}.fake-appspot.io",
                "default_bucket": f"gcs://{name}",
            }
            return (name, dict(inputs, **state))

        return ("", {})


pulumi.runtime.set_mocks(CDPStackMocks())

###############################################################################


class InfrastructureTests(unittest.TestCase):
    @pytest.mark.skipif(sys.version_info >= (3, 8), reason="Pulumi requires on Py37")
    @pulumi.runtime.test
    def test_basic_run(self) -> None:
        from cdp_backend.infrastructure import CDPStack

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
