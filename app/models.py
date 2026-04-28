from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID

from app.database import Base


class ProcessStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"


class Process(Base):
    __tablename__ = "processes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    process_id = Column(String, unique=True, index=True, nullable=False)
    total_files = Column(Integer, nullable=False, default=0)
    completed_files = Column(Integer, nullable=False, default=0)
    status = Column(String, nullable=False, default=ProcessStatus.PENDING.value)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    estimated_completion = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    process_id = Column(String, index=True, nullable=False)
    document_name = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    is_processed = Column(Boolean, nullable=False, default=False)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Result(Base):
    __tablename__ = "results"

    process_id = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    total_words = Column(Integer, nullable=False, default=0)
    total_lines = Column(Integer, nullable=False, default=0)
    total_chars = Column(Integer, nullable=False, default=0)
    most_frequent_words = Column(ARRAY(String), nullable=False, default=list)
    files_processed = Column(ARRAY(String), nullable=False, default=list)
    is_finished = Column(Boolean, nullable=True, server_default="false")
    summary = Column(Text, nullable=True)
