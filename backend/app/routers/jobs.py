from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
from enum import Enum

from app.database import get_db
from app.models import Job, JobStatus, JobStatusEvent, User
from app.schemas import JobCreate, JobUpdate, JobResponse, JobListResponse
from app.auth import get_current_user  # Import JWT auth dependency

from app.services.ai_service import generate_cover_letter

router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"]
)


class JobSort(str, Enum):
    NEWEST = "newest"
    OLDEST = "oldest"
    COMPANY = "company"
    UPDATED = "updated"


# Every sort ends with `id` as a tiebreaker. Without it, rows sharing a created_at
# have no defined order, and paging could show one job twice while skipping another.
SORT_CLAUSES = {
    JobSort.NEWEST: (Job.created_at.desc(), Job.id.desc()),
    JobSort.OLDEST: (Job.created_at.asc(), Job.id.asc()),
    JobSort.COMPANY: (Job.company_name.asc(), Job.id.asc()),
    JobSort.UPDATED: (Job.updated_at.desc(), Job.id.desc()),
}

MAX_SEARCH_LENGTH = 100


def _escape_like(term: str) -> str:
    """Escapes LIKE wildcards so a search for '100%' or 'senior_dev' matches those
    characters literally instead of treating them as pattern syntax."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

@router.get("/", response_model=JobListResponse)
def get_jobs(
    # Aliased because `status` is already bound to fastapi.status in this module
    status_filter: Optional[JobStatus] = Query(
        None, alias="status",
        description="Exact pipeline stage. An unknown value is rejected with 422."
    ),
    search: Optional[str] = Query(
        None, max_length=MAX_SEARCH_LENGTH,
        description="Case-insensitive keyword, matched against company name and job title."
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort: JobSort = Query(JobSort.NEWEST),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch job application entries belonging ONLY to the authenticated user,
    optionally filtered by status and/or keyword (US-08)."""
    # The ownership filter is the base of the query; every other filter narrows it
    query = db.query(Job).filter(Job.user_id == current_user.id)

    if status_filter is not None:
        query = query.filter(Job.status == status_filter.value)

    term = (search or "").strip()
    if term:
        # Blank and whitespace-only searches fall through as "no filter"
        pattern = f"%{_escape_like(term)}%"
        query = query.filter(or_(
            Job.company_name.ilike(pattern, escape="\\"),
            Job.job_title.ilike(pattern, escape="\\"),
        ))

    # Counted with the same filters but no limit, so it reports total matches
    # rather than the size of this page
    total = query.count()

    jobs = query.order_by(*SORT_CLAUSES[sort]).limit(limit).offset(offset).all()

    return {"items": jobs, "total": total, "limit": limit, "offset": offset}

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