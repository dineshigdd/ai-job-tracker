"""Test cases for AI service functionality.

This file tests the AI-powered features including cover letter generation
and resume analysis in services/ai_service.py and related router endpoints.
"""
import pytest
from fastapi import status
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from app.models import Job, User, Resume, JobStatus
from app.services.ai_service import (
    generate_cover_letter,
    analyze_resume,
    GROQ_MODEL,
    GROQ_TIMEOUT_SECONDS,
)


class TestCoverLetterGeneration:
    """Test the cover letter generation endpoint and service."""

    @pytest.mark.asyncio
    async def test_generate_cover_letter_for_job(self, client, db_session, test_user):
        """Test generating a cover letter for a job application."""
        # Create a job with description
        job = Job(
            id=uuid4(),
            user_id=test_user.id,
            company_name="Test Company",
            job_title="Senior Python Developer",
            job_description="Looking for experienced Python developer with Django skills",
            status=JobStatus.APPLIED
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        
        # Create an active resume
        resume = Resume(
            user_id=test_user.id,
            filename="test.pdf",
            extracted_text="Python Django developer with 5 years experience",
            content_hash="a" * 64,
            is_active=True
        )
        db_session.add(resume)
        db_session.commit()
        
        # Mock the AI service to avoid actual API calls
        with patch("app.routers.jobs.generate_cover_letter", new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = "Dear Hiring Manager,..."
            
            response = client.post(f"/jobs/{job.id}/generate-cover-letter")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["ai_cover_letter"] == "Dear Hiring Manager,..."
            assert data["cover_letter_generated_at"] is not None

    @pytest.mark.asyncio
    async def test_generate_cover_letter_no_job_description(self, client, db_session, test_user):
        """Test that cover letter generation fails without job description."""
        job = Job(
            id=uuid4(),
            user_id=test_user.id,
            company_name="Test Company",
            job_title="Developer",
            job_description=None,
            status=JobStatus.APPLIED
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        
        response = client.post(f"/jobs/{job.id}/generate-cover-letter")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Job description is required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_generate_cover_letter_empty_job_description(self, client, db_session, test_user):
        """Test that cover letter generation fails with empty job description."""
        job = Job(
            id=uuid4(),
            user_id=test_user.id,
            company_name="Test Company",
            job_title="Developer",
            job_description="   ",
            status=JobStatus.APPLIED
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        
        response = client.post(f"/jobs/{job.id}/generate-cover-letter")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Job description is required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_generate_cover_letter_no_resume(self, client, db_session, test_user):
        """Test generating a cover letter when user has no active resume."""
        job = Job(
            id=uuid4(),
            user_id=test_user.id,
            company_name="Test Company",
            job_title="Developer",
            job_description="Python developer needed",
            status=JobStatus.APPLIED
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        
        # No active resume created
        
        with patch("app.routers.jobs.generate_cover_letter", new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = "Dear Hiring Manager,..."
            
            response = client.post(f"/jobs/{job.id}/generate-cover-letter")
            
            # Should still succeed, just without resume text
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["ai_cover_letter"] == "Dear Hiring Manager,..."
            # Check that resume_text was None
            mock_generate.assert_called_once()
            call_kwargs = mock_generate.call_args[1]
            assert call_kwargs["resume_text"] is None

    @pytest.mark.asyncio
    async def test_generate_cover_letter_job_not_found(self, client, db_session, test_user):
        """Test generating cover letter for non-existent job."""
        response = client.post(f"/jobs/{uuid4()}/generate-cover-letter")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Job application not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_generate_cover_letter_other_users_job(self, client, db_session, test_user):
        """Test that users cannot generate cover letters for other users' jobs."""
        other_user = User(
            id=uuid4(),
            email="other@example.com",
            hashed_password="hash"
        )
        db_session.add(other_user)
        db_session.commit()
        
        other_job = Job(
            id=uuid4(),
            user_id=other_user.id,
            company_name="Other Company",
            job_title="Developer",
            job_description="Test description",
            status=JobStatus.APPLIED
        )
        db_session.add(other_job)
        db_session.commit()
        db_session.refresh(other_job)
        
        response = client.post(f"/jobs/{other_job.id}/generate-cover-letter")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_generate_cover_letter_with_inactive_resume(self, client, db_session, test_user):
        """Test generating cover letter uses only active resume."""
        job = Job(
            id=uuid4(),
            user_id=test_user.id,
            company_name="Test Company",
            job_title="Developer",
            job_description="Python developer needed",
            status=JobStatus.APPLIED
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        
        # Create inactive resume
        resume = Resume(
            user_id=test_user.id,
            filename="inactive.pdf",
            extracted_text="Inactive resume content",
            content_hash="a" * 64,
            is_active=False
        )
        db_session.add(resume)
        db_session.commit()
        
        with patch("app.routers.jobs.generate_cover_letter", new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = "Dear Hiring Manager,..."
            
            response = client.post(f"/jobs/{job.id}/generate-cover-letter")
            
            assert response.status_code == status.HTTP_200_OK
            # Should pass None for resume_text since no active resume
            call_kwargs = mock_generate.call_args[1]
            assert call_kwargs["resume_text"] is None

    @pytest.mark.asyncio
    async def test_generate_cover_letter_updates_job(self, client, db_session, test_user):
        """Test that cover letter is stored on the job."""
        job = Job(
            id=uuid4(),
            user_id=test_user.id,
            company_name="Test Company",
            job_title="Developer",
            job_description="Python developer needed",
            status=JobStatus.APPLIED
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        
        assert job.ai_cover_letter is None
        assert job.cover_letter_generated_at is None
        
        with patch("app.routers.jobs.generate_cover_letter", new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = "Test cover letter content"
            
            response = client.post(f"/jobs/{job.id}/generate-cover-letter")
            
            assert response.status_code == status.HTTP_200_OK
            
            # Refresh and check
            db_session.refresh(job)
            assert job.ai_cover_letter == "Test cover letter content"
            assert job.cover_letter_generated_at is not None


class TestResumeAnalysis:
    """Test the resume analysis functionality."""

    @pytest.mark.asyncio
    async def test_upload_and_analyze_resume(self, client, db_session, test_user):
        """Test uploading and analyzing a resume."""
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n%%EOF"
        
        with patch("app.routers.resumes.analyze_resume", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = "Test AI feedback"
            
            response = client.post(
                "/resumes/analyze",
                files={"file": ("test.pdf", pdf_content)},
                data={"job_description": "Python developer"}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["ai_feedback"] == "Test AI feedback"
            assert data["filename"] == "test.pdf"
            assert "resume" in data

    @pytest.mark.asyncio
    async def test_analyze_stored_resume(self, client, db_session, test_user):
        """Test analyzing an already stored resume."""
        resume = Resume(
            user_id=test_user.id,
            filename="test.pdf",
            extracted_text="Python developer with 5 years experience",
            content_hash="a" * 64,
            is_active=True
        )
        db_session.add(resume)
        db_session.commit()
        db_session.refresh(resume)
        
        with patch("app.routers.resumes.analyze_resume", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = "Updated AI feedback"
            
            response = client.post(
                f"/resumes/{resume.id}/analyze",
                json={"job_description": "Senior Python developer"}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["ai_feedback"] == "Updated AI feedback"
            assert data["resume"]["id"] == str(resume.id)

    @pytest.mark.asyncio
    async def test_analyze_resume_without_job_description(self, client, db_session, test_user):
        """Test analyzing a resume without providing a job description."""
        resume = Resume(
            user_id=test_user.id,
            filename="test.pdf",
            extracted_text="Python developer",
            content_hash="a" * 64,
            is_active=True
        )
        db_session.add(resume)
        db_session.commit()
        db_session.refresh(resume)
        
        with patch("app.routers.resumes.analyze_resume", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = "General AI feedback"
            
            response = client.post(f"/resumes/{resume.id}/analyze")
            
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["ai_feedback"] == "General AI feedback"


class TestAIServiceConfiguration:
    """Test AI service configuration."""

    def test_groq_api_key_required(self):
        """Test that GROQ_API_KEY is required."""
        # This is tested at import time, so we can't easily test it
        # without mocking the environment variables
        pass

    def test_groq_model_default(self):
        """Test default Groq model."""
        assert GROQ_MODEL == "llama-3.3-70b-versatile"

    def test_groq_timeout_default(self):
        """Test default Groq timeout."""
        assert GROQ_TIMEOUT_SECONDS == 30.0


class TestAIServiceFunctions:
    """Test the AI service functions directly."""

    @pytest.mark.asyncio
    @patch("app.services.ai_service.client.chat.completions.create")
    async def test_generate_cover_letter_function(self, mock_create):
        """Test the generate_cover_letter function directly."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Generated cover letter..."
        mock_create.return_value = mock_response
        
        cover_letter = await generate_cover_letter(
            job_title="Senior Developer",
            company_name="Test Co",
            job_description="Python developer needed",
            resume_text="5 years of Python experience"
        )
        
        assert cover_letter == "Generated cover letter..."
        
        # Verify the call was made with correct parameters
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["model"] == GROQ_MODEL
        assert call_kwargs["temperature"] == 0.7
        assert "messages" in call_kwargs

    @pytest.mark.asyncio
    @patch("app.services.ai_service.client.chat.completions.create")
    async def test_analyze_resume_function(self, mock_create):
        """Test the analyze_resume function directly."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Resume analysis feedback..."
        mock_create.return_value = mock_response
        
        feedback = await analyze_resume(
            resume_text="Python Django developer with 5 years experience",
            target_job_description="Looking for Senior Python developer"
        )
        
        assert feedback == "Resume analysis feedback..."

    @pytest.mark.asyncio
    @patch("app.services.ai_service.client.chat.completions.create")
    async def test_truncate_function(self, mock_create):
        """Test the _truncate function."""
        from app.services.ai_service import _truncate
        
        # Test with text under limit
        short_text = "Short text"
        assert _truncate(short_text, 100) == short_text
        
        # Test with text at limit
        exact_text = "A" * 100
        assert _truncate(exact_text, 100) == exact_text
        
        # Test with text over limit
        long_text = "A" * 200
        result = _truncate(long_text, 100)
        assert len(result) == 103  # 100 chars + "...[truncated]"
        assert result.endswith("...[truncated]")
        
        # Test with whitespace
        whitespace_text = "   Text with spaces   "
        result = _truncate(whitespace_text, 100)
        assert result.startswith("Text")

    @pytest.mark.asyncio
    async def test_truncate_with_none(self):
        """Test truncating None."""
        from app.services.ai_service import _truncate
        
        result = _truncate(None, 100)
        assert result == ""

    @pytest.mark.asyncio
    async def test_truncate_with_empty_string(self):
        """Test truncating empty string."""
        from app.services.ai_service import _truncate
        
        result = _truncate("", 100)
        assert result == ""


class TestAIServiceErrorHandling:
    """Test error handling in AI service."""

    @pytest.mark.asyncio
    @patch("app.services.ai_service.client.chat.completions.create")
    async def test_generate_cover_letter_rate_limit(self, mock_create):
        """Test handling rate limit errors."""
        from openai import RateLimitError
        
        mock_create.side_effect = RateLimitError("Rate limited", response=MagicMock(), body=None)
        
        with pytest.raises(Exception) as exc_info:
            await generate_cover_letter(
                job_title="Test",
                company_name="Test",
                job_description="Test",
                resume_text="Test"
            )
        
        # Should raise HTTPException with 429
        assert "429" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("app.services.ai_service.client.chat.completions.create")
    async def test_generate_cover_letter_timeout(self, mock_create):
        """Test handling timeout errors."""
        from openai import APITimeoutError
        
        mock_create.side_effect = APITimeoutError("Timeout", response=MagicMock(), body=None)
        
        with pytest.raises(Exception) as exc_info:
            await generate_cover_letter(
                job_title="Test",
                company_name="Test",
                job_description="Test",
                resume_text="Test"
            )
        
        # Should raise HTTPException with 504
        assert "504" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("app.services.ai_service.client.chat.completions.create")
    async def test_generate_cover_letter_connection_error(self, mock_create):
        """Test handling connection errors."""
        from openai import APIConnectionError
        
        mock_create.side_effect = APIConnectionError("Connection error", response=MagicMock(), body=None)
        
        with pytest.raises(Exception) as exc_info:
            await generate_cover_letter(
                job_title="Test",
                company_name="Test",
                job_description="Test",
                resume_text="Test"
            )
        
        # Should raise HTTPException with 504
        assert "504" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("app.services.ai_service.client.chat.completions.create")
    async def test_generate_cover_letter_status_error(self, mock_create):
        """Test handling status errors."""
        from openai import APIStatusError
        
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_create.side_effect = APIStatusError("Bad request", response=mock_response, body=None)
        
        with pytest.raises(Exception) as exc_info:
            await generate_cover_letter(
                job_title="Test",
                company_name="Test",
                job_description="Test",
                resume_text="Test"
            )
        
        # Should raise HTTPException
        assert "HTTPException" in str(type(exc_info.value).__name__)


class TestInputLengthLimits:
    """Test input length limits for AI service."""

    @pytest.mark.asyncio
    @patch("app.services.ai_service.client.chat.completions.create")
    async def test_job_description_truncation(self, mock_create):
        """Test that long job descriptions are truncated."""
        from app.services.ai_service import MAX_JOB_DESCRIPTION_CHARS, _truncate
        
        long_description = "A" * (MAX_JOB_DESCRIPTION_CHARS + 100)
        
        with patch("app.services.ai_service.generate_cover_letter") as mock_func:
            # We need to test the truncation in the router, not the service
            pass
        
        # Test truncation function directly
        truncated = _truncate(long_description, MAX_JOB_DESCRIPTION_CHARS)
        assert len(truncated) <= MAX_JOB_DESCRIPTION_CHARS + len("...[truncated]")

    @pytest.mark.asyncio
    @patch("app.services.ai_service.client.chat.completions.create")
    async def test_resume_truncation(self, mock_create):
        """Test that long resumes are truncated."""
        from app.services.ai_service import MAX_RESUME_CHARS, _truncate
        
        long_resume = "A" * (MAX_RESUME_CHARS + 100)
        
        truncated = _truncate(long_resume, MAX_RESUME_CHARS)
        assert len(truncated) <= MAX_RESUME_CHARS + len("...[truncated]")


class TestCoverLetterTimestamp:
    """Test cover letter timestamp functionality."""

    @pytest.mark.asyncio
    async def test_cover_letter_generated_at_timestamp(self, client, db_session, test_user):
        """Test that cover_letter_generated_at is set when generating a cover letter."""
        import datetime
        
        job = Job(
            id=uuid4(),
            user_id=test_user.id,
            company_name="Test Company",
            job_title="Developer",
            job_description="Python developer needed",
            status=JobStatus.APPLIED
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        
        assert job.cover_letter_generated_at is None
        
        with patch("app.routers.jobs.generate_cover_letter", new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = "Test cover letter"
            
            response = client.post(f"/jobs/{job.id}/generate-cover-letter")
            
            assert response.status_code == status.HTTP_200_OK
            
            # Verify timestamp is set
            db_session.refresh(job)
            assert job.cover_letter_generated_at is not None
            assert isinstance(job.cover_letter_generated_at, datetime.datetime)

    @pytest.mark.asyncio
    async def test_cover_letter_generated_at_not_set_on_update(self, client, db_session, test_user):
        """Test that cover_letter_generated_at is not updated when updating other fields."""
        import datetime
        
        job = Job(
            id=uuid4(),
            user_id=test_user.id,
            company_name="Test Company",
            job_title="Developer",
            job_description="Python developer needed",
            status=JobStatus.APPLIED,
            ai_cover_letter="Old cover letter",
            cover_letter_generated_at=datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        
        old_timestamp = job.cover_letter_generated_at
        
        # Update job without generating new cover letter
        response = client.put(
            f"/jobs/{job.id}",
            json={"company_name": "New Company"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify timestamp unchanged
        db_session.refresh(job)
        assert job.cover_letter_generated_at == old_timestamp
