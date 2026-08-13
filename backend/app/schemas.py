from pydantic import BaseModel, EmailStr
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

    class Config:
        from_attributes = True


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