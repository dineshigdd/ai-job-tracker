import enum
import uuid
from sqlalchemy import (
    CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class JobStatus(str, enum.Enum):
    """The only statuses a job may hold. Free-text statuses silently fragment the
    dashboard funnel ('Offer' vs 'Offered' vs 'offer' count as three stages)."""
    WISHLIST = "Wishlist"
    APPLIED = "Applied"
    INTERVIEWING = "Interviewing"
    OFFER = "Offer"
    REJECTED = "Rejected"


# Display order for the funnel. Alphabetical sorting would render
# Applied -> Interviewing -> Offer -> Rejected -> Wishlist, which is nonsense.
STATUS_ORDER = [
    JobStatus.WISHLIST,
    JobStatus.APPLIED,
    JobStatus.INTERVIEWING,
    JobStatus.OFFER,
    JobStatus.REJECTED,
]

# Statuses that mean "this application was actually submitted". Wishlist entries are
# excluded from conversion-rate denominators; they were never sent anywhere.
SUBMITTED_STATUSES = [s for s in STATUS_ORDER if s is not JobStatus.WISHLIST]

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to jobs (One user can have many jobs)
    jobs = relationship("Job", back_populates="owner", cascade="all, delete-orphan")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    company_name = Column(String, nullable=False)
    job_title = Column(String, nullable=False)
    job_description = Column(Text, nullable=True)
    status = Column(
        String(50),
        nullable=False,
        default=JobStatus.APPLIED.value,
        server_default=JobStatus.APPLIED.value,
    )

    # AI-powered features fields
    ai_cover_letter = Column(Text, nullable=True)
    # Existence of a letter is not the same as it being new; the dashboard's
    # "recently generated" highlight needs a timestamp
    cover_letter_generated_at = Column(DateTime(timezone=True), nullable=True)
    match_score = Column(Integer, nullable=True)

    # Scheduled interview, used for the "upcoming interviews" highlight
    interview_date = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationship back to User
    owner = relationship("User", back_populates="jobs")
    status_events = relationship(
        "JobStatusEvent", back_populates="job", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Enforced in the database so a direct SQL write cannot bypass the API
        CheckConstraint(
            "status IN ('%s')" % "', '".join(s.value for s in STATUS_ORDER),
            name="ck_jobs_status_valid",
        ),
        Index("ix_jobs_user_status", "user_id", "status"),
        Index("ix_jobs_user_created", "user_id", "created_at"),
    )


class JobStatusEvent(Base):
    """Append-only log of every status transition.

    The `jobs` table only records where an application is *now*. Conversion rates
    need to know where it has *been*: a job that went Applied -> Interviewing ->
    Rejected sits in Rejected, and counting current status alone would report a 0%
    interview rate for someone who interviewed and was turned down.
    """
    __tablename__ = "job_status_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    # Denormalised from jobs so dashboard queries never need the join
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    from_status = Column(String(50), nullable=True)  # null on a job's first event
    to_status = Column(String(50), nullable=False)
    changed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    job = relationship("Job", back_populates="status_events")

    __table_args__ = (
        Index("ix_job_status_events_user_changed", "user_id", "changed_at"),
        Index("ix_job_status_events_job", "job_id"),
    )