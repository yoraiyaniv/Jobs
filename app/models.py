import uuid
from datetime import datetime
from sqlalchemy import Column, Text, DateTime, func, Integer, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    email = Column(Text, unique=True, nullable=False)
    location = Column(Text, nullable=True)
    titles = Column(ARRAY(Text), nullable=True, default=list)
    cv_filename = Column(Text, nullable=True)
    cv_path = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(Text, nullable=False)
    location = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    job_link = Column(Text, nullable=False, unique=True)
    company_name = Column(Text, nullable=True)
    company_link = Column(Text, nullable=True)
    liked = Column(Boolean, default=None, nullable=True)  # True=liked, False=disliked, None=no action
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class JobScore(Base):
    __tablename__ = "job_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    cv_fit = Column(Integer, nullable=False)
    job_quality = Column(Integer, nullable=False)
    overall = Column(Integer, nullable=False)
    summary = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
