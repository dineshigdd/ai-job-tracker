from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models import Job, User
from app.schemas import JobCreate, JobUpdate, JobResponse

# Initialize the APIRouter with a prefix and tags for Swagger documentation
router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"]
)

# Temporary hardcoded user ID for testing until authentication/JWT is wired up
# (This matches the first user seeded in your seed.py)
TEMP_USER_ID = "d0216bad-74ff-417f-bdfc-268b7e3439fb" 
# Note: In your actual app, you'll extract this dynamically from the JWT token.

@router.get("/", response_model=List[JobResponse])
def get_jobs(db: Session = Depends(get_db)):
    """Fetch all job application entries."""
    jobs = db.query(Job).all()
    return jobs

@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(job: JobCreate, user_id: UUID, db: Session = Depends(get_db)):
    """Create a new job application tracking entry."""
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_job = Job(
        user_id=user_id,
        company_name=job.company_name,
        job_title=job.job_title,
        job_description=job.job_description,
        status=job.status,
        ai_cover_letter=job.ai_cover_letter,
        match_score=job.match_score
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job

@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: UUID, db: Session = Depends(get_db)):
    """Fetch a single job application by its UUID."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job application not found")
    return job

@router.put("/{job_id}", response_model=JobResponse)
def update_job(job_id: UUID, job_update: JobUpdate, db: Session = Depends(get_db)):
    """Update an existing job application."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job application not found")

    # Update only fields that were provided in the request
    update_data = job_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(job, key, value)

    db.commit()
    db.refresh(job)
    return job

@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: UUID, db: Session = Depends(get_db)):
    """Delete a job application entry."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job application not found")

    db.delete(job)
    db.commit()
    return None