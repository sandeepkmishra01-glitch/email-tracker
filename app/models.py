from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .db import Base


def utcnow():
    return datetime.now(timezone.utc)


class Email(Base):
    __tablename__ = "emails"
    id = Column(Integer, primary_key=True)
    subject = Column(String(500), nullable=False)
    body_html = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    messages = relationship("Message", back_populates="email", cascade="all, delete-orphan")
    links = relationship("Link", back_populates="email", cascade="all, delete-orphan")


class Link(Base):
    __tablename__ = "links"
    id = Column(Integer, primary_key=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False)
    url = Column(Text, nullable=False)
    email = relationship("Email", back_populates="links")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False)
    recipient = Column(String(320), nullable=False)
    token = Column(String(64), unique=True, index=True, nullable=False)
    sent_at = Column(DateTime(timezone=True), default=utcnow)
    email = relationship("Email", back_populates="messages")
    events = relationship("Event", back_populates="message", cascade="all, delete-orphan")


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False, index=True)
    type = Column(String(10), nullable=False)  # open | click
    link_id = Column(Integer, ForeignKey("links.id"), nullable=True)
    ip = Column(String(64))
    user_agent = Column(String(500))
    is_proxy = Column(Boolean, default=False)
    ts = Column(DateTime(timezone=True), default=utcnow)
    message = relationship("Message", back_populates="events")
