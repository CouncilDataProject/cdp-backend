from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
engine = create_engine("sqlite:///test-1.db", echo=True, future=True)

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

print("SELECTING ALL DATA")
with Session(engine) as session:
    stmt = select(Matter)
    for matter in session.scalars(stmt):
        print(matter)