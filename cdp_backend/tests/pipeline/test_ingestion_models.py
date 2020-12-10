#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import asdict
import pytest

from cdp_backend.pipeline.ingestion_models import (
    EventIngestionModel,
    EXAMPLE_MINIMAL_EVENT,
    EXAMPLE_FILLED_EVENT,
)

###############################################################################


@pytest.mark.parametrize(
    "model",
    [
        EXAMPLE_MINIMAL_EVENT,
        EXAMPLE_FILLED_EVENT,
    ],
)
def test_model_can_be_serialized(model: EventIngestionModel) -> None:
    assert isinstance(asdict(model), dict)
