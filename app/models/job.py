from typing import List, Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, ForeignKey
from app.models.base import Base, TimestampMixin, generate_uuid

class JobPosting(Base, TimestampMixin):
    __tablename__ = "job_postings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)
    requirements: Mapped[Optional[str]] = mapped_column(Text)

    company: Mapped["Company"] = relationship(back_populates="jobs")
    applications: Mapped[List["Application"]] = relationship(back_populates="job_posting", cascade="all, delete-orphan")
