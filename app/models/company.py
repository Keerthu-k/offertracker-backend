from typing import List, Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text
from app.models.base import Base, TimestampMixin, generate_uuid

class Company(Base, TimestampMixin):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    industry: Mapped[Optional[str]] = mapped_column(String(255))
    website: Mapped[Optional[str]] = mapped_column(String(255))

    jobs: Mapped[List["JobPosting"]] = relationship(back_populates="company", cascade="all, delete-orphan")
