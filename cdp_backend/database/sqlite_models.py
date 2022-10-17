from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base

from cdp_backend.database import constants


class BaseModel:
    @classmethod
    def model_lookup_by_table_name(cls, table_name):
        registry_instance = getattr(cls, "registry")
        for mapper_ in registry_instance.mappers:
            model = mapper_.class_
            model_class_name = model.__tablename__
            if model_class_name == table_name:
                return model


Base: DeclarativeMeta = declarative_base(cls=BaseModel)


class Body(Base):
    __tablename__ = constants.BODY
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime)
    is_active = Column(Boolean, nullable=False)
    external_source_id = Column(String)

    def get_class_by_tablename(self):
        return self.model_lookup_by_table_name(constants.BODY)


class Event(Base):
    __tablename__ = constants.EVENT
    id = Column(String, primary_key=True)
    body_ref = Column(String, nullable=False)
    static_thumbnail_ref = Column(String)
    hover_thumbnail_ref = Column(String)
    agenda_uri = Column(String)
    minutes_uri = Column(String)
    external_source_id = Column(String)


class EventMinutesItem(Base):
    __tablename__ = constants.EVENT_MINUTES_ITEM
    id = Column(String, primary_key=True)
    event_ref = Column(String, nullable=False)
    minutes_item_ref = Column(String, nullable=False)
    index = Column(Integer, nullable=False)
    decision = Column(String, nullable=False)
    external_source_id = Column(String)


class EventMinutesItemFile(Base):
    __tablename__ = constants.EVENT_MINUTES_ITEM_FILE
    id = Column(String, primary_key=True)
    event_minutes_item_ref = Column(String, nullable=False)
    name = Column(String, nullable=False)
    uri = Column(String, nullable=False)
    external_source_id = Column(String)


class File(Base):
    __tablename__ = constants.FILE
    id = Column(String, primary_key=True)
    uri = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    media_type = Column(String)


class Matter(Base):
    __tablename__ = constants.MATTER
    id = Column(String, primary_key=True)
    name = Column(String)
    matter_type = Column(String)
    title = Column(String)
    external_source_id = Column(String)


class MatterFile(Base):
    __tablename__ = constants.MATTER_FILE
    id = Column(String, primary_key=True)
    matter_ref = Column(String, nullable=False)
    name = Column(String, nullable=False)
    uri = Column(String)
    external_source_id = Column(String)


class MatterSponsor(Base):
    __tablename__ = constants.MATTER_SPONSOR
    id = Column(String, primary_key=True)
    matter_ref = Column(String, nullable=False)
    person_ref = Column(String, nullable=False)
    external_source_id = Column(String)


class MatterStatus(Base):
    __tablename__ = constants.MATTER_STATUS
    id = Column(String, primary_key=True)
    matter_ref = Column(String, nullable=False)
    event_minutes_item_ref = Column(String)
    status = Column(String, nullable=False)
    update_datetime = Column(DateTime, nullable=False)
    external_source_id = Column(String)


class MinutesItem(Base):
    __tablename__ = constants.MINUTES_ITEM
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    matter_ref = Column(String)
    external_source_id = Column(String)


class Person(Base):
    __tablename__ = constants.PERSON
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    router_string = Column(String)
    email = Column(String)
    phone = Column(String)
    website = Column(String)
    picture_ref = Column(String)
    is_active = Column(Boolean, nullable=False)
    external_source_id = Column(String)


class Role(Base):
    __tablename__ = constants.ROLE
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    person_ref = Column(String, nullable=False)
    body_ref = Column(String)
    seat_ref = Column(String, nullable=False)
    start_datetime = Column(String)
    end_datetime = Column(DateTime)
    external_source_id = Column(String)


class Session(Base):
    __tablename__ = constants.SESSION
    id = Column(String, primary_key=True)
    event_ref = Column(String, nullable=False)
    session_datetime = Column(DateTime, nullable=False)
    session_index = Column(Integer, nullable=False)
    session_content_hash = Column(String, nullable=False)
    video_uri = Column(String, nullable=False)
    caption_uri = Column(String)
    external_source_id = Column(String)


class Seat(Base):
    __tablename__ = constants.SEAT
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    electoral_area = Column(String)
    electoral_type = Column(String)
    image_ref = Column(String)
    external_source_id = Column(String)


class Transcript(Base):
    __tablename__ = constants.TRANSCRIPT
    id = Column(String, primary_key=True)
    session_ref = Column(String, nullable=False)
    file_ref = Column(String, nullable=False)
    generator = Column(String, nullable=False)
    confidence = Column(Integer, nullable=False)
    created = Column(DateTime, nullable=False)


class Vote(Base):
    __tablename__ = constants.VOTE
    id = Column(String, primary_key=True)
    matter_ref = Column(String, nullable=False)
    event_ref = Column(String, nullable=False)
    event_minutes_item_ref = Column(String, nullable=False)
    person_ref = Column(String, nullable=False)
    decision = Column(String, nullable=False)
    in_majority = Column(Boolean)
    external_source_id = Column(String)
