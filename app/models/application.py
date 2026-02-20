from typing import List, Optional
from datetime import datetime, date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, ForeignKey, JSON, Date
from sqlalchemy.sql import func
from app.models.base import Base, TimestampMixin, generate_uuid

class Application(Base, TimestampMixin):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    job_posting_id: Mapped[str] = mapped_column(ForeignKey("job_postings.id"), nullable=False)
    resume_version_id: Mapped[str] = mapped_column(ForeignKey("resume_versions.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Applied")
    applied_date: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    
    job_posting: Mapped["JobPosting"] = relationship(back_populates="applications")
    resume_version: Mapped[Optional["ResumeVersion"]] = relationship(back_populates="applications")
    stages: Mapped[List["ApplicationStage"]] = relationship(back_populates="application", cascade="all, delete-orphan")
    outcome: Mapped[Optional["Outcome"]] = relationship(back_populates="application", cascade="all, delete-orphan", uselist=False)
    reflection: Mapped[Optional["Reflection"]] = relationship(back_populates="application", cascade="all, delete-orphan", uselist=False)

class ApplicationStage(Base, TimestampMixin):
    __tablename__ = "application_stages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id"), nullable=False)
    stage_name: Mapped[str] = mapped_column(String(100), nullable=False)
    stage_date: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    notes: Mapped[Optional[str]] = mapped_column(Text)

    application: Mapped["Application"] = relationship(back_populates="stages")


class Outcome(Base, TimestampMixin):
    __tablename__ = "outcomes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id"), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # Offer, Rejected, Withdrawn
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    application: Mapped["Application"] = relationship(back_populates="outcome")

class Reflection(Base, TimestampMixin):
    __tablename__ = "reflections"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id"), unique=True, nullable=False)
    what_worked: Mapped[Optional[str]] = mapped_column(Text)
    what_failed: Mapped[Optional[str]] = mapped_column(Text)
    skill_gaps: Mapped[Optional[dict]] = mapped_column(JSON) # e.g. {"python": "needs advanced asyncio", "system design": "more practice"}
    improvement_plan: Mapped[Optional[str]] = mapped_column(Text)

    application: Mapped["Application"] = relationship(back_populates="reflection")
