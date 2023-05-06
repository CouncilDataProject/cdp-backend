from sqlalchemy import Boolean, Column, DateTime, Integer, String, ForeignKey
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


class File(Base):
    __tablename__ = constants.FILE
    id = Column(String, primary_key=True)
    uri = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    media_type = Column(String)

    def get_class_by_tablename(self):
        return self.model_lookup_by_table_name(constants.FILE)


class Person(Base):
    __tablename__ = constants.PERSON
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    router_string = Column(String, nullable=False)
    email = Column(String)
    phone = Column(String)
    website = Column(String)
    picture_id = Column(Integer, ForeignKey(File.id))
    is_active = Column(Boolean, nullable=False)
    external_source_id = Column(String)

    def get_class_by_tablename(self):
        return self.model_lookup_by_table_name(constants.PERSON)


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


class Seat(Base):
    __tablename__ = constants.SEAT
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    electoral_area = Column(String)
    electoral_type = Column(String)
    image_id = Column(String, ForeignKey(File.id))
    external_source_id = Column(String)

    def get_class_by_tablename(self):
        return self.model_lookup_by_table_name(constants.SEAT)


class Role(Base):
    __tablename__ = constants.ROLE
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    person_id = Column(String, ForeignKey(Person.id), nullable=False)
    body_id = Column(String, ForeignKey(Body.id))
    seat_id = Column(String, ForeignKey(Seat.id), nullable=False)
    start_datetime = Column(String, nullable=False)
    end_datetime = Column(DateTime)
    external_source_id = Column(String)

    def get_class_by_tablename(self):
        return self.model_lookup_by_table_name(constants.ROLE)


class Matter(Base):
    __tablename__ = constants.MATTER
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    matter_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    external_source_id = Column(String)

    def get_class_by_tablename(self):
        return self.model_lookup_by_table_name(constants.MATTER)


class MatterFile(Base):
    __tablename__ = constants.MATTER_FILE
    id = Column(String, primary_key=True)
    matter_id = Column(Integer, ForeignKey(Matter.id), nullable=False)
    name = Column(String, nullable=False)
    uri = Column(String, nullable=False)
    external_source_id = Column(String)

    def get_class_by_tablename(self):
        return self.model_lookup_by_table_name(constants.MATTER_FILE)


class MatterSponsor(Base):
    __tablename__ = constants.MATTER_SPONSOR
    id = Column(String, primary_key=True)
    matter_ref = Column(Integer, ForeignKey(Matter.id), nullable=False)
    person_ref = Column(Integer, ForeignKey(Person.id), nullable=False)
    external_source_id = Column(String)

    def get_class_by_tablename(self):
        return self.model_lookup_by_table_name(constants.MATTER_SPONSOR)


class MinutesItem(Base):
    __tablename__ = constants.MINUTES_ITEM
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    matter_id = Column(Integer, ForeignKey(Matter.id))
    external_source_id = Column(String)

    def get_class_by_tablename(self):
        return self.model_lookup_by_table_name(constants.MINUTES_ITEM)


class Event(Base):
    __tablename__ = constants.EVENT
    id = Column(String, primary_key=True)
    event_datetime = Column(DateTime, nullable=False)
    body_id = Column(String, ForeignKey(Body.id), nullable=False)
    static_thumbnail_id = Column(String, ForeignKey(File.id))
    hover_thumbnail_id = Column(String, ForeignKey(File.id))
    agenda_uri = Column(String)
    minutes_uri = Column(String)
    external_source_id = Column(String)

    def get_class_by_tablename(self):
        return self.model_lookup_by_table_name(constants.EVENT)


class Session(Base):
    __tablename__ = constants.SESSION
    id = Column(String, primary_key=True)
    event_id = Column(String, ForeignKey(Event.id), nullable=False)
    session_datetime = Column(DateTime, nullable=False)
    session_index = Column(Integer, nullable=False)
    session_content_hash = Column(String, nullable=False)
    video_uri = Column(String, nullable=False)
    caption_uri = Column(String)
    external_source_id = Column(String)

    def get_class_by_tablename(self):
        return self.model_lookup_by_table_name(constants.SESSION)


class Transcript(Base):
    __tablename__ = constants.TRANSCRIPT
    id = Column(String, primary_key=True)
    session_id = Column(String, nullable=False)
    file_id = Column(String, ForeignKey(File.id), nullable=False)
    generator = Column(String, nullable=False)
    confidence = Column(Integer, nullable=False)
    created = Column(DateTime, nullable=False)

    def get_class_by_tablename(self):
        return self.model_lookup_by_table_name(constants.TRANSCRIPT)


class EventMinutesItem(Base):
    __tablename__ = constants.EVENT_MINUTES_ITEM
    id = Column(String, primary_key=True)
    event_id = Column(Integer, ForeignKey(Event.id), nullable=False)
    minutes_item_id = Column(Integer, ForeignKey(MinutesItem.id), nullable=False)
    index = Column(Integer, nullable=False)
    decision = Column(String, nullable=False)
    external_source_id = Column(String)

    def get_class_by_tablename(self):
        return self.model_lookup_by_table_name(constants.EVENT_MINUTES_ITEM)


class MatterStatus(Base):
    __tablename__ = constants.MATTER_STATUS
    id = Column(String, primary_key=True)
    matter_id = Column(Integer, ForeignKey(Matter.id), nullable=False)
    event_minutes_item_id = Column(Integer, ForeignKey(EventMinutesItem.id))
    status = Column(String, nullable=False)
    update_datetime = Column(DateTime, nullable=False)
    external_source_id = Column(String)

    def get_class_by_tablename(self):
        return self.model_lookup_by_table_name(constants.MATTER_STATUS)


class EventMinutesItemFile(Base):
    __tablename__ = constants.EVENT_MINUTES_ITEM_FILE
    id = Column(String, primary_key=True)
    event_minutes_item_id = Column(Integer, ForeignKey(EventMinutesItem.id), nullable=False)
    name = Column(String, nullable=False)
    uri = Column(String, nullable=False)
    external_source_id = Column(String)

    def get_class_by_tablename(self):
        return self.model_lookup_by_table_name(constants.EVENT_MINUTES_ITEM_FILE)


class Vote(Base):
    __tablename__ = constants.VOTE
    id = Column(String, primary_key=True)
    matter_id = Column(String, ForeignKey(Matter.id), nullable=False)
    event_id = Column(String, ForeignKey(Event.id), nullable=False)
    event_minutes_item_id = Column(String, ForeignKey(EventMinutesItem.id), nullable=False)
    person_id = Column(String, ForeignKey(Person.id), nullable=False)
    decision = Column(String, nullable=False)
    in_majority = Column(Boolean)
    external_source_id = Column(String)

    def get_class_by_tablename(self):
        return self.model_lookup_by_table_name(constants.VOTE)