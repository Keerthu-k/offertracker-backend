from typing import List, Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text
from app.models.base import Base, TimestampMixin, generate_uuid

class ResumeVersion(Base, TimestampMixin):
    __tablename__ = "resume_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    version_name: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    file_url: Mapped[Optional[str]] = mapped_column(String(500))

    applications: Mapped[List["Application"]] = relationship(back_populates="resume_version", cascade="all, delete-orphan")
