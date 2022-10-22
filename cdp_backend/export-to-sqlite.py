from cdp_data import CDPInstances
from cdp_data.utils import connect_to_infrastructure
from fireo.models import Model
from google.cloud.firestore_v1.transaction import Transaction
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cdp_backend.database import models as db_models
from cdp_backend.database import sqlite_models
from cdp_backend.database.constants import (
    BODY,
    EVENT,
    EVENT_MINUTES_ITEM,
    EVENT_MINUTES_ITEM_FILE,
    FILE,
    MATTER,
    MATTER_FILE,
    MATTER_SPONSOR,
    MATTER_STATUS,
    MINUTES_ITEM,
    PERSON,
    ROLE,
    SEAT,
    SESSION,
    TRANSCRIPT,
    VOTE,
)

# Init transaction and auth
# fireo.connection(from_file=".keys/cdp-albuquerque-1d29496e.json")
# Connect to the database
connect_to_infrastructure(CDPInstances.Albuquerque)
engine = create_engine("sqlite:///test.db", echo=True, future=True)

# Create tables!
sqlite_models.Base.metadata.create_all(engine, tables=None, checkfirst=True)

MODEL_NAME = 'model_name'
ACTUAL_MODEL = 'actual_model'

model_list = [
    {
        MODEL_NAME: BODY,  
        ACTUAL_MODEL: db_models.Body
    },
    {
        MODEL_NAME: EVENT,  
        ACTUAL_MODEL: db_models.Event
    },
    {
        MODEL_NAME: EVENT_MINUTES_ITEM,
        ACTUAL_MODEL: db_models.EventMinutesItem
    },
    {
        MODEL_NAME: EVENT_MINUTES_ITEM_FILE,
        ACTUAL_MODEL: db_models.EventMinutesItemFile
    },
    {
        MODEL_NAME: FILE,
        ACTUAL_MODEL: db_models.File
    },
    {
        MODEL_NAME: MATTER,
        ACTUAL_MODEL: db_models.Matter
    },
    {
        MODEL_NAME: MATTER_FILE,
        ACTUAL_MODEL: db_models.MatterFile
    },
    {
        MODEL_NAME: MATTER_SPONSOR,
        ACTUAL_MODEL: db_models.MatterSponsor
    },
    {
        MODEL_NAME: MATTER_STATUS,
        ACTUAL_MODEL: db_models.MatterStatus
    },
    {
        MODEL_NAME: MINUTES_ITEM,
        ACTUAL_MODEL: db_models.MinutesItem
    },
    {
        MODEL_NAME: PERSON,
        ACTUAL_MODEL: db_models.Person
    },
    {
        MODEL_NAME: ROLE,
        ACTUAL_MODEL: db_models.Role
    },
    {
        MODEL_NAME: SESSION,
        ACTUAL_MODEL: db_models.Session
    },
    {
        MODEL_NAME: SEAT,
        ACTUAL_MODEL: db_models.Seat
    },
    {
        MODEL_NAME: TRANSCRIPT,
        ACTUAL_MODEL: db_models.Transcript
    },
    {
        MODEL_NAME: VOTE,
        ACTUAL_MODEL: db_models.Vote
    },
]


def get_sql_schema(model_name: str) -> Model:
    if model_name == BODY:
        return sqlite_models.Body()
    elif model_name == EVENT:
        return sqlite_models.Event()
    elif model_name == EVENT_MINUTES_ITEM:
        return sqlite_models.EventMinutesItem()
    elif model_name == EVENT_MINUTES_ITEM_FILE:
        return sqlite_models.EventMinutesItemFile()
    elif model_name == FILE:
        return sqlite_models.File()
    elif model_name == MATTER:
        return sqlite_models.Matter()
    elif model_name == MATTER_FILE:
        return sqlite_models.MatterFile()
    elif model_name == MATTER_SPONSOR:
        return sqlite_models.MatterSponsor()
    elif model_name == MATTER_STATUS:
        return sqlite_models.MatterStatus()
    elif model_name == MINUTES_ITEM:
        return sqlite_models.MinutesItem()
    elif model_name == PERSON:
        return sqlite_models.Person()
    elif model_name == ROLE:
        return sqlite_models.Role()
    elif model_name == SESSION:
        return sqlite_models.Session()
    elif model_name == SEAT:
        return sqlite_models.Seat()
    elif model_name == TRANSCRIPT:
        return sqlite_models.Transcript()
    elif model_name == VOTE:
        return sqlite_models.Vote()
    else:
        return


def get_schema_properties(sql_schema: Model, doc: Transaction) -> Model:
    model = sql_schema
    model.id = doc.id

    if model.get_class_by_tablename() == type(sqlite_models.Body()):
        model.name = doc.name
        model.description = doc.description
        model.start_datetime = doc.start_datetime
        model.is_active = doc.is_active
        model.external_source_id = doc.external_source_id
    elif model.get_class_by_tablename() == type(sqlite_models.Event()):
        model.body_id = doc.body_ref.get().id        
        model.event_datetime = doc.event_datetime.get().id 
        model.static_thumbnail_id = doc.static_thumbnail_ref.get().id 
        model.hover_thumbnail_id = doc.hover_thumbnail_ref.get().id 
        model.agenda_uri = doc.agenda_uri
        model.minutes_uri = doc.minutes_uri
        model.external_source_id = doc.external_source_id
    elif model.get_class_by_tablename() == type(sqlite_models.EventMinutesItem()):
        model.event_id = doc.event_ref.get().id
        model.minutes_item_id = doc.minutes_item_ref.get().id
        model.index = doc.index
        model.decision = doc.decision
    elif model.get_class_by_tablename() == type(sqlite_models.EventMinutesItemFile()):
        model.event_minutes_item_id = doc.event_minutes_item_ref.get().id
        model.name = doc.name
        model.uri = doc.uri
        model.external_source_id = doc.external_source_id
    elif model.get_class_by_tablename() == type(sqlite_models.File()):
        model.uri = doc.uri
        model.name = doc.name
        model.description = doc.description
        model.media_type = doc.media_type
    elif model.get_class_by_tablename() == type(sqlite_models.Matter()):
        model.name = doc.name
        model.matter_type = doc.matter_type
        model.title = doc.title
        model.external_source_id = doc.external_source_id
    elif model.get_class_by_tablename() == type(sqlite_models.MatterFile()):
        model.matter_id = doc.matter_ref.get().id
        model.name = doc.name
        model.uri = doc.uri
        model.external_source_id = doc.external_source_id
    elif model.get_class_by_tablename() == type(sqlite_models.MatterSponsor()):
        model.matter_id = doc.matter_ref.get().id
        model.person_id = doc.person_ref.get().id
        model.external_source_id = doc.external_source_id
    elif model.get_class_by_tablename() == type(sqlite_models.MatterStatus()):
        model.matter_id = doc.matter_ref.get().id 
        model.event_minutes_item_id = doc.event_minutes_item_ref.get().id 
        model.status = doc.status
        model.update_datetime = doc.update_datetime
        model.external_source_id = doc.external_source_id
    elif model.get_class_by_tablename() == type(sqlite_models.MinutesItem()):
        model.name = doc.name
        model.description = doc.description
        model.matter_id = doc.matter_ref.get().id
        model.external_source_id = doc.external_source_id
    elif model.get_class_by_tablename() == type(sqlite_models.Person()):
        model.name = doc.name
        model.router_string = doc.router_string
        model.email = doc.email
        model.phone = doc.phone
        model.website = doc.website
        model.picture_id = doc.picture_ref.get().id
        model.is_active = doc.is_active
        model.external_source_id = doc.external_source_id
    elif model.get_class_by_tablename() == type(sqlite_models.Role()):
        model.title = doc.title
        model.person_id = doc.person_ref.get().id
        model.body_id = doc.body_ref.get().id
        model.seat_id = doc.seat_ref.get().id
        model.start_datetime = doc.start_datetime
        model.end_datetime = doc.end_datetime
        model.external_source_id = doc.external_source_id
    elif model.get_class_by_tablename() == type(sqlite_models.Session()):
        model.event_id = doc.event_ref.get().id
        model.session_datetime = doc.session_datetime
        model.session_index = doc.session_index
        model.session_content_hash = doc.session_content_hash
        model.video_uri = doc.video_uri
        model.caption_uri = doc.caption_uri
        model.external_source_id = doc.external_source_id
    elif model.get_class_by_tablename() == type(sqlite_models.Seat()):
        model.name = doc.name
        model.electoral_area = doc.electoral_area
        model.electoral_type = doc.electoral_type
        model.image_id = doc.image_ref.get().id
        model.external_source_id = doc.external_source_id
    elif model.get_class_by_tablename() == type(sqlite_models.Transcript()):
        model.session_id = doc.session_ref.get().id
        model.file_id = doc.file_ref.get().id
        model.generator = doc.generator
        model.confidence = doc.confidence
        model.created = doc.created
    elif model.get_class_by_tablename() == type(sqlite_models.Vote()):
        model.matter_id = doc.matter_ref.get().id
        model.event_id = doc.event_ref.get().id
        model.event_minutes_item_ref = doc.event_minutes_item_ref.get().id
        model.person_id = doc.person_ref.get().id
        model.decision = doc.decision
        model.in_majority = doc.in_majority
        model.external_source_id = doc.external_source_id
    return model


with Session(engine) as session:
    for model in model_list:
        name = model.get(MODEL_NAME)
        print(f"STARTING INSERTS on modelname: {name}")

        collection_iter = model.get(ACTUAL_MODEL).collection.fetch()

        sql_schema = None
        doc_idx = 0
        for docRef in collection_iter:
            # if element in doc is first
            sql_schema = get_sql_schema(name)
            # print(f'docRef:: {docRef}') # this appears to be a custom python object? expected a firestore document reference (maybe it is typed that way?)
            sql_model = get_schema_properties(sql_schema, docRef)

            session.add(sql_model)

            doc_idx += 1

        print("COMMITTING INSERTS")
        session.commit()


# from sqlalchemy import select
# print("SELECTING ALL DATA")
# with Session(engine) as session:
#     stmt = select(sqlite_models.Event)
#     for event in session.scalars(stmt):
#         print(event)
