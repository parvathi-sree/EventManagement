from sqlalchemy import Column, Integer, String, DateTime, Enum, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()


class EventStatus(str, enum.Enum):
    scheduled = "scheduled"
    ongoing = "ongoing"
    completed = "completed"
    canceled = "canceled"


class Event(Base):
    __tablename__ = 'events'

    event_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    location = Column(String)
    max_attendees = Column(Integer)
    status = Column(Enum(EventStatus), default=EventStatus.scheduled)

    attendees = relationship("Attendee", back_populates="event")

    def __repr__(self):
        return f"<Event(id={self.event_id}, name={self.name}, status={self.status})>"


class Attendee(Base):
    __tablename__ = 'attendees'

    attendee_id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique=True, index=True)
    phone_number = Column(String)
    event_id = Column(Integer, ForeignKey('events.event_id'))

    event = relationship("Event", back_populates="attendees")
    check_in_status = Column(Boolean, default=False)

    def __repr__(self):
        return f"<Attendee(id={self.attendee_id}, email={self.email}, checked_in={self.check_in_status})>"
