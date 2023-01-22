#!/usr/bin/env python

from dataclasses import asdict

import pytest

from cdp_backend.pipeline.ingestion_models import (
    EXAMPLE_FILLED_EVENT,
    EXAMPLE_MINIMAL_EVENT,
    EventIngestionModel,
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
