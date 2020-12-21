#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cdp_backend.pipeline import event_gather_pipeline as pipeline
import cdp_backend.database.models as db_models
import cdp_backend.pipeline.ingestion_models as ingestion_models
from cdp_backend.database.validators import UniquenessValidation
from cdp_backend.bin.event_gather import example_get_events_func

from prefect import Flow
from unittest import mock


db_body_example = db_models.Body.Example()
ingestion_body = ingestion_models.Body(
    name=db_body_example.name, is_active=db_body_example.is_active
)


def test_create_event_gather_flow() -> None:
    with mock.patch("fireo.connection") as mock_connector:
        mock_connector.return_value = None
        flow = pipeline.create_event_gather_flow(example_get_events_func, "/fake/path")
        assert isinstance(flow, Flow)


def test_upload_body_unique() -> None:
    with mock.patch(
        "cdp_backend.pipeline.event_gather_pipeline.get_model_uniqueness"
    ) as mock_uniqueness_validator:
        mock_uniqueness_validator.return_value = UniquenessValidation(
            True, [db_body_example]
        )

        with mock.patch("fireo.models.Model.save") as mock_saver:
            mock_saver.return_value = None

            db_body = pipeline.upload_body.run(ingestion_body)
            assert db_body.name == ingestion_body.name
            assert db_body.is_active == ingestion_body.is_active


def test_upload_body_not_unique() -> None:
    with mock.patch(
        "cdp_backend.pipeline.event_gather_pipeline.get_model_uniqueness"
    ) as mock_uniqueness_validator:
        mock_uniqueness_validator.return_value = UniquenessValidation(
            False, [db_body_example]
        )

        db_body = pipeline.upload_body.run(ingestion_body)
        assert db_body.name == ingestion_body.name
        assert db_body.is_active == ingestion_body.is_active
