from cdp_backend.database import models as db_models
from cdp_data import CDPInstances
from cdp_data.utils import connect_to_infrastructure

# Init transaction and auth
# fireo.connection(from_file=".keys/cdp-albuquerque-1d29496e.json")
# Connect to the database
connect_to_infrastructure(CDPInstances.Albuquerque)

from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Matter(Base):
    __tablename__ = "matter"
    id = Column(String, primary_key=True)
    name = Column(String)
    matter_type = Column(String)
    title = Column(String)
    external_source_id = Column(String)
    def __repr__(self):
        return f"Matter(id={self.id!r}, name={self.name!r})"

from sqlalchemy import create_engine
engine = create_engine("sqlite:///test-1.db", echo=True, future=True)

# Create tables!
Base.metadata.create_all(engine, tables=None, checkfirst=True)

from sqlalchemy.orm import Session

with Session(engine) as session:
    matter_iter = db_models.Matter.collection.fetch()
    print("STARTING INSERTS")
    for matter in matter_iter:
        sql_model = Matter(
            id=matter.id,
            name=matter.name,
            matter_type=matter.matter_type,
            title=matter.title,
            external_source_id=matter.external_source_id,
        )
        session.add(sql_model)

    print("COMMITTING INSERTS")
    session.commit()

from sqlalchemy import select

print("SELECTING ALL DATA")
with Session(engine) as session:
    stmt = select(Matter)
    for matter in session.scalars(stmt):
        print(matter)
