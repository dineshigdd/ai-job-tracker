from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID

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
    status: Optional[str] = "Applied"
    ai_cover_letter: Optional[str] = None
    match_score: Optional[int] = None

class JobCreate(JobBase):
    pass

class JobUpdate(BaseModel):
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    job_description: Optional[str] = None
    status: Optional[str] = None
    ai_cover_letter: Optional[str] = None
    match_score: Optional[int] = None

class JobResponse(JobBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True