from pydantic import BaseModel, EmailStr, Field
from typing import Dict, List, Optional
from datetime import date, datetime
from uuid import UUID

from app.models import JobStatus

# --- USER SCHEMAS ---

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# --- JOB SCHEMAS ---

class JobBase(BaseModel):
    company_name: str
    job_title: str
    job_description: Optional[str] = None
    # Typed as the enum so an unknown status is rejected with a 422 at the edge,
    # instead of silently creating a new bucket in the dashboard funnel
    status: JobStatus = JobStatus.APPLIED
    ai_cover_letter: Optional[str] = None
    match_score: Optional[int] = None
    interview_date: Optional[datetime] = None

class JobCreate(JobBase):
    pass

class JobStatusEventResponse(BaseModel):
    id: UUID
    job_id: UUID
    from_status: Optional[str] = None
    to_status: str
    changed_at: datetime

    class Config:
        from_attributes = True

class JobUpdate(BaseModel):
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    job_description: Optional[str] = None
    status: Optional[JobStatus] = None
    ai_cover_letter: Optional[str] = None
    match_score: Optional[int] = None
    interview_date: Optional[datetime] = None

class JobResponse(JobBase):
    id: UUID
    user_id: UUID
    # Server-managed, so it is readable but not settable by the client
    cover_letter_generated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    status_events: List[JobStatusEventResponse] = []

    class Config:
        from_attributes = True

class JobListResponse(BaseModel):
    """Paginated envelope for GET /jobs/. `total` counts every row matching the
    filters, not the rows on this page, so the client can render "1-50 of 213"."""
    items: List[JobResponse]
    total: int
    limit: int
    offset: int


# --- RESUME SCHEMAS ---

class ResumeSummary(BaseModel):
    """A stored resume *without* its text.

    Extracted text runs to thousands of characters, and no list view renders it, so
    it is left out here and served only by the single-resume detail endpoint.
    """
    id: UUID
    user_id: UUID
    filename: str
    # SHA-256 of the text. Also the version a match score is cached against.
    content_hash: str
    is_active: bool
    extracted_text_length: int
    created_at: datetime

    class Config:
        from_attributes = True

class ResumeDetail(ResumeSummary):
    extracted_text: str

class ResumeAnalysisResponse(BaseModel):
    """Response of both analyze endpoints. `filename`, `extracted_text_length` and
    `ai_feedback` are kept at the top level so the original upload-and-analyze
    contract still holds; `resume` carries what is now persisted."""
    filename: str
    extracted_text_length: int
    ai_feedback: str
    resume: ResumeSummary


# --- MATCH SCORE SCHEMAS ---

class MatchScoreRequest(BaseModel):
    """Body of `POST /jobs/{job_id}/match-score`.

    ATS-matching-scorer.md §5.1 specifies `resume_text` here, but flags it as a
    workaround for there being nowhere to store a resume, to be replaced by
    `resume_id` "once a resumes table lands". It has landed, so this is the replacement
    (§13, step 8): the server reads the text itself, which is what lets it record
    *which* resume version produced a score, and stops a multi-megabyte resume being
    posted on every scoring call (§9.3).
    """
    resume_id: Optional[UUID] = Field(
        None,
        description="Resume to score against. Defaults to the user's active resume.",
    )


class MatchScoreComponent(BaseModel):
    """One weighted component of the score.

    `available=False` means the inputs could not be evaluated, *not* that the candidate
    scored zero — the confusion between those two is what made an empty resume score 90
    (§0, D3). An unavailable component has `score=None`, is excluded from the weighted
    average, and carries a `reason` the UI should show instead of a number.
    """
    score: Optional[float] = None
    available: bool
    reason: Optional[str] = None


class SkillMatchComponent(MatchScoreComponent):
    matched_skills: List[str] = []
    missing_skills: List[str] = []


class ExperienceMatchComponent(MatchScoreComponent):
    user_experience: str
    required_experience: str


class MatchScoreBreakdown(BaseModel):
    """§5.1's breakdown block.

    Note `keyword_density` is an object here, not the bare number §5.1 shows. Every
    component needs to be able to report itself unavailable, and a bare int has nowhere
    to put that. Frontend reading this must use `keyword_density.score`.
    """
    hard_skills: SkillMatchComponent
    soft_skills: SkillMatchComponent
    experience: ExperienceMatchComponent
    keyword_density: MatchScoreComponent


class MatchScoreResponse(BaseModel):
    """`match_score` is null, never 0, when no component could be evaluated — the same
    no-data-is-not-a-zero rule the dashboard uses for conversion rates (§3.4)."""
    job_id: UUID
    match_score: Optional[int] = None
    interpretation: str
    breakdown: MatchScoreBreakdown
    suggestions: List[str] = []
    # Set when a guard rail altered the headline number, e.g. the §3.4 cap applied to a
    # pairing that shares no recognised skills
    notes: List[str] = []

    # Which resume produced this, and under which algorithm. `resume_version` is the
    # content hash, so a stored score can be checked for staleness without diffing text.
    resume_id: UUID
    resume_filename: str
    resume_version: str
    algorithm_version: str
    calculated_at: datetime


# --- DASHBOARD SCHEMAS ---

class FunnelBlock(BaseModel):
    counts: Dict[str, int]
    total_tracked: int
    total_applications: int

class RatesBlock(BaseModel):
    # None (not 0.0) when there are no applications yet: "no data" and
    # "you converted nothing" are very different messages to show a user
    interview_rate: Optional[float] = None
    offer_rate: Optional[float] = None
    response_rate: Optional[float] = None

class ActivityItem(BaseModel):
    type: str
    job_id: UUID
    company_name: str
    job_title: str
    from_status: Optional[str] = None
    to_status: str
    occurred_at: datetime

class UpcomingInterview(BaseModel):
    job_id: UUID
    company_name: str
    job_title: str
    interview_date: datetime

class TrendPoint(BaseModel):
    period_start: date
    applications: int

class TrendBlock(BaseModel):
    bucket: str
    points: List[TrendPoint]

class DashboardStats(BaseModel):
    generated_at: datetime
    range: str
    funnel: FunnelBlock
    rates: RatesBlock
    recent_activity: List[ActivityItem]
    upcoming_interviews: List[UpcomingInterview]
    trend: TrendBlock