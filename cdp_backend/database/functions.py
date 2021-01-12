#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

import fireo
from fireo.models import Model
from prefect import task

from ..database import exceptions
from ..database.validators import get_model_uniqueness
from ..pipeline.ingestion_models import IngestionModel

###############################################################################

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)4s: %(module)s:%(lineno)4s %(asctime)s] %(message)s",
)
log = logging.getLogger(__name__)

###############################################################################


def update_db_model(
    db_model: Model,
    ingestion_model: IngestionModel,
) -> Model:
    """
    Compare an existing database model to an ingestion model and if the non-primary
    fields are different, update the database model.

    Parameters
    ----------
    db_model: Model
        The existing database model to compare new data against.
    ingestion_model: IngestionModel
        The data to compare against and potentially use for updating.

    Returns
    -------
    db_model: Model
        The updated database model.
    """
    # Filter out base class attrs, unrelated class methods, primary keys
    non_primary_db_fields = [
        attr
        for attr in dir(db_model)
        if (
            not attr.startswith("_")
            and attr not in dir(Model)
            and attr not in db_model._PRIMARY_KEYS
        )
    ]

    needs_update = False
    for field in non_primary_db_fields:
        if hasattr(ingestion_model, field):
            db_val = getattr(db_model, field)
            ingestion_val = getattr(ingestion_model, field)

            # If values are different, use the ingestion value
            # Make sure we don't overwrite with empty values
            if db_val != ingestion_val and ingestion_val is not None:
                setattr(db_model, field, ingestion_val)
                needs_update = True
                log.info(
                    f"Updating {db_model.key} {field} from {db_val} to {ingestion_val}."
                )

    # Avoid unnecessary db interactions
    if needs_update:
        db_model.update(db_model.key)

    return db_model


def upload_db_model(
    db_model: Model,
    ingestion_model: IngestionModel,
    creds_file: str,
) -> Model:
    """
    Upload or update an existing database model.

    Parameters
    ----------
    db_model: Model
        The database model to upload.
    ingestion_model: IngestionModel
        The accompanying ingestion model in the case the model already exists and needs
        to be updated rather than inserted.
    creds_file: str
        Path to Google Service Account Credentials JSON file.

    Returns
    -------
    db_model: Model
        The uploaded, or updated, database model.

    Raises
    ------
    exceptions.UniquenessError
        More than one (1) conflicting model was found in the database. This should
        never occur and indicates that something is wrong with the database.
    """
    # Initialize fireo connection
    fireo.connection(from_file=creds_file)

    uniqueness_validation = get_model_uniqueness(db_model)
    if uniqueness_validation.is_unique:
        db_model.save()
        log.info(
            f"Saved new {db_model.__class__.__name__} with document id={db_model.id}."
        )
    elif len(uniqueness_validation.conflicting_models) == 1:
        updated_db_model = update_db_model(
            uniqueness_validation.conflicting_models[0],
            ingestion_model,
        )

        return updated_db_model
    else:
        raise exceptions.UniquenessError(
            model=db_model, conflicting_results=uniqueness_validation.conflicting_models
        )

    return db_model


@task
def upload_db_model_task(
    db_model: Model,
    ingestion_model: IngestionModel,
    creds_file: str,
) -> Model:
    # Wraps the standard Python function in Prefect task
    return upload_db_model(
        db_model=db_model, ingestion_model=ingestion_model, creds_file=creds_file
    )
