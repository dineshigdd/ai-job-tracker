from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from datetime import datetime, timezone

from app.database import get_db
from app.models import Job, JobStatusEvent, User
from app.schemas import JobCreate, JobUpdate, JobResponse
from app.auth import get_current_user  # Import JWT auth dependency

from app.services.ai_service import generate_cover_letter

router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"]
)

@router.get("/", response_model=List[JobResponse])
def get_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch all job application entries belonging ONLY to the authenticated user."""
    jobs = db.query(Job).filter(Job.user_id == current_user.id).all()
    return jobs

@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    job: JobCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new job application tracking entry tied to the current user."""
    new_job = Job(
        user_id=current_user.id,
        company_name=job.company_name,
        job_title=job.job_title,
        job_description=job.job_description,
        status=job.status,
        ai_cover_letter=job.ai_cover_letter,
        match_score=job.match_score,
        interview_date=job.interview_date
    )
    db.add(new_job)
    db.flush()  # assigns new_job.id without ending the transaction

    # First entry in this job's history. Without it the job is invisible to every
    # dashboard conversion metric, which reads history rather than current status.
    db.add(JobStatusEvent(
        job_id=new_job.id,
        user_id=current_user.id,
        from_status=None,
        to_status=new_job.status
    ))

    db.commit()
    db.refresh(new_job)
    return new_job

@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: UUID, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch a single job application by its UUID, verifying it belongs to the user."""
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job application not found")
    return job

@router.put("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: UUID, 
    job_update: JobUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing job application belonging to the user."""
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job application not found")

    previous_status = job.status

    # Update only fields that were provided in the request
    update_data = job_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(job, key, value)

    # Record the transition, but only when the status genuinely changed. A PUT that
    # resends the same status must not fill the activity feed with no-op entries.
    if job.status != previous_status:
        db.add(JobStatusEvent(
            job_id=job.id,
            user_id=current_user.id,
            from_status=previous_status,
            to_status=job.status
        ))

    db.commit()
    db.refresh(job)
    return job

@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: UUID, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a job application entry belonging to the user."""
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job application not found")

    db.delete(job)
    db.commit()
    return None


@router.post("/{job_id}/generate-cover-letter", response_model=JobResponse)
async def create_ai_cover_letter(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generates an AI cover letter for an existing job application using the AI service."""
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job application not found")

    if not job.job_description or not job.job_description.strip():
        raise HTTPException(status_code=400, detail="Job description is required to generate a cover letter")

    # Groq call: async so the event loop stays free during the several seconds
    # this takes. It raises HTTPException itself on rate limits / timeouts /
    # upstream errors, and nothing has been written yet at this point.
    cover_letter = await generate_cover_letter(
        job_title=job.job_title,
        company_name=job.company_name,
        job_description=job.job_description
    )

    job.ai_cover_letter = cover_letter
    # Timestamp it so the dashboard can highlight *newly* generated letters;
    # the column alone only proves one exists, not that it is recent
    job.cover_letter_generated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)

    return job