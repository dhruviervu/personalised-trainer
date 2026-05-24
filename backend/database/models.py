"""
SQLAlchemy ORM models for training sessions, sets, and personal records.
"""

import datetime
import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, default="Athlete")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    goal = Column(String, default="strength")
    bodyweight_logs = relationship("BodyweightLog", back_populates="user")
    sessions = relationship("Session", back_populates="user")


class BodyweightLog(Base):
    __tablename__ = "bodyweight_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"))
    weight_kg = Column(Float)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    user = relationship("User", back_populates="bodyweight_logs")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    exercise = Column(String)
    goal = Column(String)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    completed = Column(Boolean, default=False)
    progression_advice = Column(String, nullable=True)
    total_volume_kg = Column(Float, default=0)
    sets = relationship("SetLog", back_populates="session", order_by="SetLog.set_number")
    user = relationship("User", back_populates="sessions")


class SetLog(Base):
    __tablename__ = "set_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    set_number = Column(Integer)
    weight_kg = Column(Float)
    reps_completed = Column(Integer)
    good_reps = Column(Integer)
    bad_reps = Column(Integer)
    rpe = Column(Float, nullable=True)
    form_flags = Column(JSON)
    avg_angles = Column(JSON)
    form_score = Column(Float)
    e1rm = Column(Float)
    coach_feedback = Column(String, nullable=True)
    session = relationship("Session", back_populates="sets")


class PersonalRecord(Base):
    __tablename__ = "personal_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"))
    exercise = Column(String)
    weight_kg = Column(Float)
    reps = Column(Integer)
    e1rm = Column(Float)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    session_id = Column(String, ForeignKey("sessions.id"))
