import io
import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from starlette.concurrency import run_in_threadpool

from app.models import User
from app.auth import get_current_user
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


@router.post("/analyze")
async def upload_and_analyze_resume(
    file: UploadFile = File(...),
    job_description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads a PDF resume, extracts its text, and returns AI-driven feedback.
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

    # analyze_resume raises its own HTTPException on rate limits / timeouts /
    # upstream errors, so those pass through with their real status codes
    feedback = await analyze_resume(
        resume_text=extracted_text,
        target_job_description=job_description
    )

    return {
        "filename": filename,
        "extracted_text_length": len(extracted_text),
        "ai_feedback": feedback
    }
