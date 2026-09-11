"""SQLAlchemy models for the family tree data model: people, their charts, and the
relationship edges between them (per PROJECT_BRIEF.md's Data Model section)."""

from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Time, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Person(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    birth_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    system: Mapped[str] = mapped_column(String, nullable=False, default="western_tropical")
    utc_offset_override: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chart: Mapped[Chart] = relationship(
        back_populates="person", uselist=False, cascade="all, delete-orphan"
    )


class Chart(Base):
    """Cached calculate_chart() output for a person, computed once at person-creation
    time. Planets/aspects are stored as JSON rather than normalized into their own
    tables -- the thread detector and other analysis features read them as plain
    dicts, and there's no query need yet to justify a per-planet row."""

    __tablename__ = "charts"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(
        ForeignKey("people.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    resolved_timezone: Mapped[str | None] = mapped_column(String, nullable=True)
    utc_offset_hours: Mapped[float] = mapped_column(Float, nullable=False)
    utc_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    julian_day_ut: Mapped[float] = mapped_column(Float, nullable=False)
    house_system: Mapped[str] = mapped_column(String, nullable=False)
    house_system_fallback_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    houses_reliable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    house_cusps: Mapped[list] = mapped_column(JSON, nullable=False)
    ascendant: Mapped[float] = mapped_column(Float, nullable=False)
    midheaven: Mapped[float] = mapped_column(Float, nullable=False)
    planets: Mapped[list] = mapped_column(JSON, nullable=False)
    aspects: Mapped[list] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    person: Mapped[Person] = relationship(back_populates="chart")


class Relationship(Base):
    __tablename__ = "relationships"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_a_id: Mapped[int] = mapped_column(
        ForeignKey("people.id", ondelete="CASCADE"), nullable=False
    )
    person_b_id: Mapped[int] = mapped_column(
        ForeignKey("people.id", ondelete="CASCADE"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(String, nullable=False)
    generation_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
