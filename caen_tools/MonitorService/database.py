from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

# from sqlalchemy import create_engine


class Base(DeclarativeBase):
    pass


class DataRows(Base):
    __tablename__ = "datarows"

    id: Mapped[int] = mapped_column(primary_key=True)
    current: Mapped[float]
    voltage: Mapped[float]
    channel: Mapped[str]
    timestamp: Mapped[int]

    def __repr__(self):
        return f"DataRow (id={self.id!r}, ch={self.channel!r}, t={self.timestamp!r})"
