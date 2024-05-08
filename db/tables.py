from __future__ import annotations
import logging
import datetime
from contextlib import contextmanager
from sqlalchemy import String, create_engine, ForeignKey, UniqueConstraint
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    DeclarativeBase,
    sessionmaker,
    relationship,
)

from data import modules


_logger = logging.getLogger(__name__)

engine = create_engine(
    url="sqlite:///db.sqlite",
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
)

Session = sessionmaker(bind=engine)


@contextmanager
def get_session() -> Session:
    """Get session"""
    new_session = Session()
    try:
        yield new_session
    finally:
        new_session.close()


class BaseTable(DeclarativeBase):
    pass


class WaUser(BaseTable):
    """Whatsapp user details"""

    __tablename__ = "wa_user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    wa_id: Mapped[str] = mapped_column(String(15), unique=True)
    name: Mapped[str] = mapped_column(String(30))
    active: Mapped[bool] = mapped_column(default=True)
    banned: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime.datetime]
    topic_id: Mapped[int] = mapped_column(ForeignKey("topic.id"))
    topic: Mapped[Topic] = relationship(back_populates="user", lazy="joined")
    messages: Mapped[list[Message]] = relationship(back_populates="user")

    __table_args__ = (UniqueConstraint("topic_id"),)


class Topic(BaseTable):
    """Topic details"""

    __tablename__ = "topic"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(unique=True)
    name: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime.datetime]
    user: Mapped[WaUser] = relationship(back_populates="topic", lazy="joined")
    messages: Mapped[list[Message]] = relationship(back_populates="topic")


class Message(BaseTable):
    """Message details"""

    __tablename__ = "message"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    topic_msg_id: Mapped[int] = mapped_column(unique=True)
    wa_msg_id: Mapped[str] = mapped_column(unique=True)
    sent_from_tg: Mapped[bool]
    created_at: Mapped[datetime.datetime]

    topic_id: Mapped[int] = mapped_column(ForeignKey("topic.id"))
    topic: Mapped[Topic] = relationship(back_populates="messages", lazy="joined")
    user_id: Mapped[int] = mapped_column(ForeignKey("wa_user.id"))
    user: Mapped[WaUser] = relationship(back_populates="messages", lazy="joined")


class MessageToSend(BaseTable):
    """Send message details"""

    __tablename__ = "message_to_send"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type_event: Mapped[modules.EventType] = mapped_column(unique=True)
    text: Mapped[str]
    created_at: Mapped[datetime.datetime]


class Settings(BaseTable):
    """Settings details"""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    wa_chat_opened_enable: Mapped[bool] = mapped_column(default=False)
    wa_welcome_msg: Mapped[bool] = mapped_column(default=False)
    wa_mark_as_read: Mapped[bool] = mapped_column(default=False)


BaseTable.metadata.create_all(engine)
