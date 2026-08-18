"""ATS match score endpoints (`docs/ATS-matching-scorer.md` §5).

Two routes, and the split between them is worth stating plainly:

  GET   previews a score without touching the database.
  POST  computes the same thing and commits it to `jobs.match_score`.

Both compute live rather than reading a stored breakdown. §4.2 measured the algorithm
in single-digit milliseconds, so recomputing costs less than the machinery needed to
keep a cached breakdown honest — and it can never serve a score from a resume the user
has since replaced. `jobs.match_score` still persists the headline number, because the
job list and the `min_score`/`max_score` filters need it in SQL.

No new tables. §6.2 proposes `match_score_history` and `match_score_breakdown`; neither
is required to use the feature, and history only becomes meaningful once there is
something to compare across time (§13, Phase 2 step 9).
"""
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Job, Resume, User
from app.schemas import MatchScoreRequest, MatchScoreResponse
from app.services.match_score import MatchScoreResult, calculate_match_score

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/jobs",
    tags=["Match Score"]
)


def _get_owned_job(db: Session, user: User, job_id: UUID) -> Job:
    """Loads one of the caller's jobs, or 404s.

    Another user's job is reported as "not found" rather than "forbidden", so the
    endpoint never confirms that a given id exists on someone else's account — the same
    rule `resumes.py` applies.
    """
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(
            status_code=404, detail="Job application not found"
        )
    return job


def _get_scoring_resume(db: Session, user: User, resume_id: Optional[UUID]) -> Resume:
    """The resume to score against: the one named, or the user's active one."""
    if resume_id is not None:
        resume = db.query(Resume).filter(
            Resume.id == resume_id, Resume.user_id == user.id
        ).first()
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        return resume

    resume = db.query(Resume).filter(
        Resume.user_id == user.id, Resume.is_active.is_(True)
    ).first()
    if not resume:
        # 400 rather than 404: the job exists and the request is well formed, but the
        # account is missing a prerequisite the user can supply (§5.5)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No active resume to score against. "
                "Upload one via POST /resumes/analyze, or pass a resume_id."
            ),
        )
    return resume


def _score(job: Job, resume: Resume) -> MatchScoreResult:
    """Runs the scorer over a job/resume pair.

    An absent job description is not an error: §11.3 calls for falling back to the job
    title, which carries real signal — "Senior Backend Engineer" states both a seniority
    level and a discipline. The scorer reports the components it could not evaluate.
    """
    return calculate_match_score(
        job_description=job.job_description or "",
        resume_text=resume.extracted_text,
        job_title=job.job_title or "",
    )


def _to_response(job: Job, resume: Resume, result: MatchScoreResult) -> dict:
    """Maps the service's dataclasses onto the API contract (§5.1).

    `asdict` rather than handing the dataclasses to Pydantic directly: the components
    carry internal fields the API has no business exposing (each one's `weight`, and
    experience's parsed `user_years`/`required_years`), and Pydantic drops unknown keys
    from a dict without needing `from_attributes` on four models to do it.
    """
    return {
        "job_id": job.id,
        "match_score": result.final_score,
        "interpretation": result.interpretation,
        "breakdown": {
            "hard_skills": asdict(result.hard_skills),
            "soft_skills": asdict(result.soft_skills),
            "experience": asdict(result.experience),
            "keyword_density": asdict(result.keyword_density),
        },
        "suggestions": result.suggestions,
        "notes": result.notes,
        "resume_id": resume.id,
        "resume_filename": resume.filename,
        "resume_version": resume.resume_version,
        "algorithm_version": result.algorithm_version,
        "calculated_at": datetime.now(timezone.utc),
    }


@router.post("/{job_id}/match-score", response_model=MatchScoreResponse)
def calculate_job_match_score(
    job_id: UUID,
    payload: Optional[MatchScoreRequest] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Scores a job against a resume and stores the result on the job.

    200, not 201 (§5.1): this updates an existing job rather than creating a resource
    at a new URL.

    The body is optional — `POST` with no body at all scores against the active resume.
    """
    job = _get_owned_job(db, current_user, job_id)
    resume = _get_scoring_resume(
        db, current_user, payload.resume_id if payload else None
    )

    result = _score(job, resume)

    # Persisted so the job list, the dashboard and the min_score/max_score filters can
    # read it in SQL. Null is stored as null: "we could not evaluate this" and "this is
    # a zero match" must not collapse into the same number (§3.4).
    job.match_score = result.final_score
    db.commit()
    db.refresh(job)

    return _to_response(job, resume, result)


@router.get("/{job_id}/match-score", response_model=MatchScoreResponse)
def get_job_match_score(
    job_id: UUID,
    resume_id: Optional[UUID] = Query(
        None, description="Resume to score against. Defaults to the active resume."
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns the full breakdown for a job without storing anything.

    Computed fresh on every call, so it always reflects the resume as it stands now.
    Use `POST` to commit the number to the job.
    """
    job = _get_owned_job(db, current_user, job_id)
    resume = _get_scoring_resume(db, current_user, resume_id)

    return _to_response(job, resume, _score(job, resume))
