from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.declarative import as_declarative
from sqlalchemy.ext.declarative import declared_attr
from typing import Any

@as_declarative()
class Base:
    id: Any
    __name__: str

    # to generate tablename from classname
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
    
    # create_time: Mapped[datetime] = mapped_column(
    #     DateTime(timezone=True), server_default=func.now()
    # )
    # update_time: Mapped[datetime] = mapped_column(
    #     DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    # )
