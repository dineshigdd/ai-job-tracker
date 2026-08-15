import io
import logging
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile, status
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from uuid import UUID

from app.database import get_db
from app.models import Resume, User, hash_resume_text
from app.auth import get_current_user
from app.schemas import ResumeAnalysisResponse, ResumeDetail, ResumeSummary
from app.services.ai_service import analyze_resume

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/resumes",
    tags=["Resumes"]
)

# Resumes are a couple of pages; anything larger is a mistake or an attack.
# The whole upload is held in memory, so this cap matters.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
PDF_MAGIC = b"%PDF"

# Stored resumes are unbounded TEXT, so the row count needs a ceiling for the same
# reason the upload size does. Well past what any real job hunt produces.
MAX_RESUMES_PER_USER = 25


def _extract_text(contents: bytes) -> str:
    """Pulls the text out of a PDF. Sync and CPU-bound, so callers run it in a thread."""
    reader = PdfReader(io.BytesIO(contents))

    if reader.is_encrypted:
        # Try the empty password, which is enough for "print-protected" PDFs
        try:
            if reader.decrypt("") == 0:
                raise PdfReadError("Resume PDF is password protected")
        except NotImplementedError as exc:  # unsupported encryption scheme
            raise PdfReadError("Unsupported PDF encryption") from exc

    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n".join(pages).strip()


def _get_owned_resume(db: Session, user: User, resume_id: UUID) -> Resume:
    """Loads one of the caller's resumes, or 404s.

    Someone else's resume is reported as "not found" rather than "forbidden", so the
    endpoint never confirms that a given id exists on another account.
    """
    resume = db.query(Resume).filter(
        Resume.id == resume_id, Resume.user_id == user.id
    ).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume


def _activate(db: Session, user_id, resume: Resume) -> None:
    """Makes `resume` the user's active one, clearing the previous holder first.

    Order matters: `uq_resumes_user_active` is a partial unique index, checked per
    statement rather than at commit, so clearing the old row and setting the new one
    in a single flush can trip it. The clear is flushed on its own first.
    """
    db.query(Resume).filter(
        Resume.user_id == user_id,
        Resume.id != resume.id,
        Resume.is_active.is_(True),
    ).update({Resume.is_active: False}, synchronize_session="fetch")
    db.flush()

    resume.is_active = True
    db.flush()


def _store_resume(db: Session, user: User, filename: str, extracted_text: str) -> Resume:
    """Persists parsed resume text and makes it the active resume."""
    content_hash = hash_resume_text(extracted_text)

    def _find_duplicate():
        return db.query(Resume).filter(
            Resume.user_id == user.id, Resume.content_hash == content_hash
        ).first()

    # Identical content is the same resume, not a new version: reuse the row instead
    # of creating one that differs only by timestamp. This keeps any match score
    # cached against that version valid, and honours uq_resumes_user_content.
    existing = _find_duplicate()
    if existing:
        _activate(db, user.id, existing)
        db.commit()
        db.refresh(existing)
        return existing

    stored_count = db.query(Resume).filter(Resume.user_id == user.id).count()
    if stored_count >= MAX_RESUMES_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"You have reached the limit of {MAX_RESUMES_PER_USER} stored resumes. "
                "Delete an older one before uploading another."
            ),
        )

    # Created inactive, then activated by _activate, so only one statement ever
    # sets is_active=True and the partial unique index sees a clean sequence
    resume = Resume(
        user_id=user.id,
        filename=filename,
        extracted_text=extracted_text,
        content_hash=content_hash,
        is_active=False,
    )
    db.add(resume)

    try:
        db.flush()
    except IntegrityError:
        # Two identical uploads raced; the other one landed first
        db.rollback()
        existing = _find_duplicate()
        if existing is None:
            logger.exception("Could not store resume %r for user %s", filename, user.id)
            raise HTTPException(status_code=500, detail="Could not store this resume")
        _activate(db, user.id, existing)
        db.commit()
        db.refresh(existing)
        return existing

    _activate(db, user.id, resume)
    db.commit()
    db.refresh(resume)
    return resume


@router.post("/analyze", response_model=ResumeAnalysisResponse)
async def upload_and_analyze_resume(
    file: UploadFile = File(...),
    job_description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads a PDF resume, stores its extracted text, and returns AI-driven feedback.
    """
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF resume files are accepted"
        )

    contents = await file.read()

    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty"
        )

    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            # Literal 413: Starlette renamed this constant, so the name differs by version
            status_code=413,
            detail=f"Resume must be smaller than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB"
        )

    # A .pdf extension proves nothing; check the actual file signature
    if not contents.startswith(PDF_MAGIC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This file is not a valid PDF"
        )

    try:
        # Parsing is sync and CPU-bound; keep it off the event loop
        extracted_text = await run_in_threadpool(_extract_text, contents)
    except PdfReadError as exc:
        logger.warning("Could not read resume PDF %r: %s", filename, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read this PDF. It may be corrupted or password protected."
        )
    except Exception:
        # Log the real cause, but don't hand internals back to the client
        logger.exception("Unexpected failure parsing resume PDF %r", filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not process this PDF."
        )

    if not extracted_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract any text from this PDF. It might be scanned or image-based."
        )

    # Stored before the AI call, and committed. Groq is rate limited on the free tier,
    # and losing the upload because the analysis failed would force the user to find
    # and re-upload the file; instead the resume is saved and only feedback is missing.
    # Storage is sync SQLAlchemy, so keep it off the event loop as well.
    resume = await run_in_threadpool(
        _store_resume, db, current_user, filename[:255], extracted_text
    )

    # analyze_resume raises its own HTTPException on rate limits / timeouts /
    # upstream errors, so those pass through with their real status codes
    feedback = await analyze_resume(
        resume_text=extracted_text,
        target_job_description=job_description
    )

    return {
        "filename": resume.filename,
        "extracted_text_length": resume.extracted_text_length,
        "ai_feedback": feedback,
        "resume": resume,
    }


@router.get("/", response_model=List[ResumeSummary])
def list_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists the caller's stored resumes, newest first. Text is omitted; fetch a
    single resume to read it."""
    return (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc(), Resume.id.desc())
        .all()
    )


# Declared before /{resume_id} so "active" is matched as a literal path, not parsed
# as a (malformed) UUID
@router.get("/active", response_model=ResumeDetail)
def get_active_resume(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns the resume match scoring uses by default."""
    resume = db.query(Resume).filter(
        Resume.user_id == current_user.id, Resume.is_active.is_(True)
    ).first()
    if not resume:
        raise HTTPException(
            status_code=404,
            detail="No active resume. Upload one via POST /resumes/analyze."
        )
    return resume


@router.get("/{resume_id}", response_model=ResumeDetail)
def get_resume(
    resume_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetches one stored resume, including its extracted text."""
    return _get_owned_resume(db, current_user, resume_id)


@router.post("/{resume_id}/analyze", response_model=ResumeAnalysisResponse)
async def analyze_stored_resume(
    resume_id: UUID,
    job_description: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Re-runs the AI analysis on an already-stored resume.

    This is the point of storing the text: feedback can be requested against a
    different job description without asking the user for the PDF again.
    """
    resume = _get_owned_resume(db, current_user, resume_id)

    feedback = await analyze_resume(
        resume_text=resume.extracted_text,
        target_job_description=job_description
    )

    return {
        "filename": resume.filename,
        "extracted_text_length": resume.extracted_text_length,
        "ai_feedback": feedback,
        "resume": resume,
    }


@router.put("/{resume_id}/activate", response_model=ResumeSummary)
def activate_resume(
    resume_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Makes this the resume scoring uses by default, demoting the previous one."""
    resume = _get_owned_resume(db, current_user, resume_id)

    if not resume.is_active:
        _activate(db, current_user.id, resume)
        db.commit()
        db.refresh(resume)

    return resume


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(
    resume_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deletes a stored resume."""
    resume = _get_owned_resume(db, current_user, resume_id)
    was_active = resume.is_active

    db.delete(resume)
    db.flush()

    # Deleting the active resume must not leave the account with resumes but nothing
    # to score against, so the newest survivor is promoted
    if was_active:
        replacement = (
            db.query(Resume)
            .filter(Resume.user_id == current_user.id)
            .order_by(Resume.created_at.desc(), Resume.id.desc())
            .first()
        )
        if replacement:
            _activate(db, current_user.id, replacement)

    db.commit()
    return None
