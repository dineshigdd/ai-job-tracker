import enum
import hashlib
import uuid
from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer,
    String, Text, UniqueConstraint, text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


def hash_resume_text(extracted_text: str) -> str:
    """SHA-256 of the parsed resume text, used as `Resume.content_hash`.

    This doubles as the resume *version*: re-uploading an unchanged PDF yields the
    same hash, so any match score cached against that version stays valid. Hashing
    the extracted text rather than the PDF bytes is deliberate — re-exporting the
    same resume changes the bytes but not the content the scorer reads.
    """
    return hashlib.sha256((extracted_text or "").encode("utf-8")).hexdigest()


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
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to jobs (One user can have many jobs)
    jobs = relationship("Job", back_populates="owner", cascade="all, delete-orphan")
    resumes = relationship(
        "Resume", back_populates="owner", cascade="all, delete-orphan"
    )


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


class Resume(Base):
    """A parsed resume belonging to a user.

    `POST /resumes/analyze` used to extract a PDF's text, send it to the AI and throw
    it away. Nothing could then be scored, versioned or recalculated later. This table
    keeps the parsed text so match scoring has something to read, and so a score can
    record *which* resume produced it.

    Only the extracted text is stored, never the uploaded PDF: the scorer never needs
    the original bytes, and keeping them would mean owning binary blob storage.
    """
    __tablename__ = "resumes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    filename = Column(String(255), nullable=False)  # original upload name
    extracted_text = Column(Text, nullable=False)
    # SHA-256 of extracted_text. This *is* the resume version scores are cached against.
    content_hash = Column(String(64), nullable=False)

    # The resume scoring uses by default when the caller names no specific one.
    is_active = Column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    owner = relationship("User", back_populates="resumes")

    __table_args__ = (
        # Re-uploading an identical resume must reuse the existing row rather than
        # create a version that only differs by timestamp
        UniqueConstraint("user_id", "content_hash", name="uq_resumes_user_content"),
        # At most one active resume per user, enforced in the database. A partial
        # unique index is the only way to say "unique among the active rows";
        # both dialects the project runs on support one.
        Index(
            "uq_resumes_user_active",
            "user_id",
            unique=True,
            postgresql_where=text("is_active"),
            sqlite_where=text("is_active"),
        ),
        # Resume list for a user, newest first
        Index("ix_resumes_user_created", "user_id", "created_at"),
    )

    @property
    def resume_version(self) -> str:
        """Alias used by match scoring, which versions on resume content."""
        return self.content_hash

    @property
    def extracted_text_length(self) -> int:
        """Character count, so list responses can describe a resume without
        shipping several thousand characters of text per row."""
        return len(self.extracted_text or "")