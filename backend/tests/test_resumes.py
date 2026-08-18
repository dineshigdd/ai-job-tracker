"""Test cases for resume management functionality.

This file tests the resume upload, storage, retrieval, analysis, and management
enpoints in routers/resumes.py.
"""
import io
import pytest
from datetime import datetime, timedelta, timezone
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from app.models import Resume, User, Job, JobStatus
from app.schemas import ResumeSummary, ResumeDetail


class TestResumeUploadAndAnalyze:
    """Test the POST /resumes/analyze endpoint."""

    def test_upload_valid_pdf(self, client, db_session, test_user, pdf_bytes,
                              mock_resume_analysis):
        """Test uploading a valid PDF resume."""
        response = client.post(
            "/resumes/analyze",
            files={"file": ("test_resume.pdf", pdf_bytes)},
            data={"job_description": "Python developer"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "filename" in data
        assert data["filename"] == "test_resume.pdf"
        assert "extracted_text_length" in data
        assert "ai_feedback" in data
        assert "resume" in data
        assert "id" in data["resume"]
        assert data["resume"]["user_id"] == str(test_user.id)
        assert data["resume"]["is_active"] is True

    def test_upload_without_job_description(self, client, db_session, test_user,
                                            pdf_bytes, mock_resume_analysis):
        """Test uploading a PDF without job description (optional)."""
        response = client.post(
            "/resumes/analyze",
            files={"file": ("test_resume.pdf", pdf_bytes)},
            data={}  # No job_description
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "ai_feedback" in data
        assert data["resume"]["is_active"] is True
        # The analyser is still called, just with nothing to compare against
        assert mock_resume_analysis.call_args[1]["target_job_description"] is None

    def test_upload_non_pdf_file(self, client, db_session, test_user):
        """Test uploading a non-PDF file is rejected."""
        text_content = b"This is not a PDF"
        
        response = client.post(
            "/resumes/analyze",
            files={"file": ("test.txt", text_content)},
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Only PDF" in response.json()["detail"]

    def test_upload_empty_file(self, client, db_session, test_user):
        """Test uploading an empty file is rejected."""
        response = client.post(
            "/resumes/analyze",
            files={"file": ("empty.pdf", b"")},
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "empty" in response.json()["detail"].lower()

    def test_upload_file_too_large(self, client, db_session, test_user):
        """Test uploading a file that exceeds the size limit."""
        # 5MB + 1 byte
        large_content = b"%PDF-1.4\n" + b"A" * (5 * 1024 * 1024 + 1)
        
        response = client.post(
            "/resumes/analyze",
            files={"file": ("large.pdf", large_content)},
        )
        
        assert response.status_code == 413
        assert "smaller than 5 MB" in response.json()["detail"]

    def test_upload_invalid_pdf_magic(self, client, db_session, test_user):
        """Test uploading a file without PDF magic bytes is rejected."""
        fake_pdf = b"This is not a real PDF"
        
        response = client.post(
            "/resumes/analyze",
            files={"file": ("fake.pdf", fake_pdf)},
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "not a valid PDF" in response.json()["detail"]

    def test_upload_password_protected_pdf(self, client, db_session, test_user):
        """Test uploading a password-protected PDF is rejected."""
        # This is a simplified test - real password-protected PDFs are more complex
        # but the handler checks for encryption
        with patch("app.routers.resumes.PdfReader") as mock_pdf:
            mock_reader = MagicMock()
            mock_reader.is_encrypted = True
            mock_reader.decrypt.return_value = 0  # Wrong password
            mock_pdf.return_value = mock_reader
            
            pdf_content = b"%PDF-1.4\n..."
            
            response = client.post(
                "/resumes/analyze",
                files={"file": ("protected.pdf", pdf_content)},
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "password" in response.json()["detail"].lower()

    def test_duplicate_resume_reuses_existing(self, client, db_session, test_user,
                                              pdf_bytes, mock_resume_analysis):
        """Test uploading the same PDF twice reuses the existing resume."""
        # First upload
        response1 = client.post(
            "/resumes/analyze",
            files={"file": ("test_resume.pdf", pdf_bytes)},
        )
        assert response1.status_code == status.HTTP_200_OK
        resume_id_1 = response1.json()["resume"]["id"]

        # Second upload with same content
        response2 = client.post(
            "/resumes/analyze",
            files={"file": ("test_resume_copy.pdf", pdf_bytes)},
        )
        assert response2.status_code == status.HTTP_200_OK
        resume_id_2 = response2.json()["resume"]["id"]

        # Should reuse the same resume
        assert resume_id_1 == resume_id_2
        assert db_session.query(Resume).filter(
            Resume.user_id == test_user.id
        ).count() == 1

    def test_resume_stored_with_correct_data(self, client, db_session, test_user,
                                             pdf_bytes, mock_resume_analysis):
        """Test that resume data is stored correctly in database."""
        response = client.post(
            "/resumes/analyze",
            files={"file": ("my_resume.pdf", pdf_bytes)},
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify in database
        resume = db_session.query(Resume).filter(Resume.user_id == test_user.id).first()
        assert resume is not None
        assert resume.filename == "my_resume.pdf"
        assert resume.is_active is True
        assert resume.content_hash is not None
        assert len(resume.content_hash) == 64  # SHA-256 hex
        # The text really came out of the PDF, rather than the row being stored empty
        assert "Python Django developer" in resume.extracted_text


class TestResumeList:
    """Test the GET /resumes/ endpoint."""

    def test_list_resumes_empty(self, client, db_session, test_user):
        """Test listing resumes when user has none."""
        response = client.get("/resumes/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_resumes_with_data(self, client, db_session, test_user):
        """Test listing resumes when user has multiple."""
        # Timestamps are set explicitly because every row in a single commit gets the
        # same server-side now(). The list orders by (created_at DESC, id DESC), so with
        # identical timestamps the random UUID tiebreak decided the order and this
        # assertion passed or failed at random.
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for i in range(3):
            resume = Resume(
                user_id=test_user.id,
                filename=f"resume_{i}.pdf",
                extracted_text=f"Resume content {i}",
                content_hash=f"{i:064x}",  # 64 chars, matching the column width
                is_active=(i == 0),  # First one is active
                created_at=base + timedelta(hours=i),
            )
            db_session.add(resume)
        db_session.commit()

        response = client.get("/resumes/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3
        # Check ordering (newest first)
        assert data[0]["filename"] == "resume_2.pdf"
        assert data[1]["filename"] == "resume_1.pdf"
        assert data[2]["filename"] == "resume_0.pdf"
        # Only one should be active
        active_count = sum(1 for r in data if r["is_active"])
        assert active_count == 1

    def test_list_only_own_resumes(self, client, db_session, test_user):
        """Test that users can only list their own resumes."""
        # Create a resume for another user
        other_user = User(
            id=uuid4(),
            email="other@example.com",
            hashed_password="hash"
        )
        db_session.add(other_user)
        db_session.commit()
        
        other_resume = Resume(
            user_id=other_user.id,
            filename="other_resume.pdf",
            extracted_text="Other user content",
            content_hash="a" * 64,
            is_active=True
        )
        db_session.add(other_resume)
        db_session.commit()
        
        # List resumes - should not see other user's resume
        response = client.get("/resumes/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 0  # Only own resumes (none for test_user)


class TestResumeDetail:
    """Test the GET /resumes/{resume_id} endpoint."""

    def test_get_resume_success(self, client, db_session, test_user):
        """Test retrieving a specific resume."""
        # Create a resume
        resume = Resume(
            user_id=test_user.id,
            filename="test.pdf",
            extracted_text="Test content",
            content_hash="a" * 64,
            is_active=True
        )
        db_session.add(resume)
        db_session.commit()
        db_session.refresh(resume)
        
        response = client.get(f"/resumes/{resume.id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(resume.id)
        assert data["filename"] == "test.pdf"
        assert data["extracted_text"] == "Test content"
        assert "extracted_text_length" in data
        assert data["extracted_text_length"] == 12

    def test_get_nonexistent_resume(self, client, db_session, test_user):
        """Test getting a resume that doesn't exist."""
        response = client.get(f"/resumes/{uuid4()}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_get_other_users_resume(self, client, db_session, test_user):
        """Test getting a resume belonging to another user."""
        other_user = User(
            id=uuid4(),
            email="other@example.com",
            hashed_password="hash"
        )
        db_session.add(other_user)
        db_session.commit()
        
        other_resume = Resume(
            user_id=other_user.id,
            filename="other.pdf",
            extracted_text="Other content",
            content_hash="b" * 64,
            is_active=True
        )
        db_session.add(other_resume)
        db_session.commit()
        db_session.refresh(other_resume)
        
        response = client.get(f"/resumes/{other_resume.id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestActiveResume:
    """Test the GET /resumes/active endpoint."""

    def test_get_active_resume_success(self, client, db_session, test_user):
        """Test getting the active resume."""
        # Create active resume
        active_resume = Resume(
            user_id=test_user.id,
            filename="active.pdf",
            extracted_text="Active content",
            content_hash="a" * 64,
            is_active=True
        )
        db_session.add(active_resume)
        db_session.commit()
        
        response = client.get("/resumes/active")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(active_resume.id)
        assert data["is_active"] is True

    def test_get_active_resume_none(self, client, db_session, test_user):
        """Test getting active resume when none exists."""
        response = client.get("/resumes/active")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "No active resume" in response.json()["detail"]

    def test_get_active_resume_with_inactive(self, client, db_session, test_user):
        """Test getting active resume when only inactive ones exist."""
        inactive_resume = Resume(
            user_id=test_user.id,
            filename="inactive.pdf",
            extracted_text="Inactive content",
            content_hash="b" * 64,
            is_active=False
        )
        db_session.add(inactive_resume)
        db_session.commit()
        
        response = client.get("/resumes/active")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestStoredResumeAnalyze:
    """Test the POST /resumes/{resume_id}/analyze endpoint."""

    def test_analyze_stored_resume(self, client, db_session, test_user,
                                   mock_resume_analysis):
        """Test analyzing an already-stored resume with a job description."""
        # Create a resume
        resume = Resume(
            user_id=test_user.id,
            filename="test.pdf",
            extracted_text="Python Django developer with 5 years experience",
            content_hash="a" * 64,
            is_active=True
        )
        db_session.add(resume)
        db_session.commit()
        db_session.refresh(resume)

        response = client.post(
            f"/resumes/{resume.id}/analyze",
            json={"job_description": "Looking for Python Django developer"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["filename"] == "test.pdf"
        assert "ai_feedback" in data
        assert data["resume"]["id"] == str(resume.id)
        # The point of storing the text: the stored copy is what gets re-analysed,
        # rather than the user being asked for the PDF again
        assert mock_resume_analysis.call_args[1]["resume_text"] == resume.extracted_text

    def test_analyze_stored_resume_no_job_description(self, client, db_session,
                                                      test_user, mock_resume_analysis):
        """Test analyzing a stored resume without job description."""
        resume = Resume(
            user_id=test_user.id,
            filename="test.pdf",
            extracted_text="Python Django developer",
            content_hash="a" * 64,
            is_active=True
        )
        db_session.add(resume)
        db_session.commit()
        db_session.refresh(resume)

        response = client.post(f"/resumes/{resume.id}/analyze")

        assert response.status_code == status.HTTP_200_OK
        assert "ai_feedback" in response.json()

    def test_analyze_nonexistent_resume(self, client, db_session, test_user):
        """Test analyzing a resume that doesn't exist."""
        response = client.post(
            f"/resumes/{uuid4()}/analyze",
            json={"job_description": "Test"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestResumeActivation:
    """Test the PUT /resumes/{resume_id}/activate endpoint."""

    def test_activate_resume(self, client, db_session, test_user):
        """Test activating a resume."""
        # Create two resumes, one active
        resume1 = Resume(
            user_id=test_user.id,
            filename="resume1.pdf",
            extracted_text="Content 1",
            content_hash="a" * 64,
            is_active=True
        )
        resume2 = Resume(
            user_id=test_user.id,
            filename="resume2.pdf",
            extracted_text="Content 2",
            content_hash="b" * 64,
            is_active=False
        )
        db_session.add_all([resume1, resume2])
        db_session.commit()
        db_session.refresh(resume1)
        db_session.refresh(resume2)
        
        # Activate resume2
        response = client.put(f"/resumes/{resume2.id}/activate")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(resume2.id)
        assert data["is_active"] is True
        
        # Verify resume1 is no longer active
        db_session.refresh(resume1)
        db_session.refresh(resume2)
        assert resume1.is_active is False
        assert resume2.is_active is True

    def test_activate_already_active_resume(self, client, db_session, test_user):
        """Test activating a resume that's already active."""
        resume = Resume(
            user_id=test_user.id,
            filename="active.pdf",
            extracted_text="Content",
            content_hash="a" * 64,
            is_active=True
        )
        db_session.add(resume)
        db_session.commit()
        db_session.refresh(resume)
        
        response = client.put(f"/resumes/{resume.id}/activate")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_active"] is True

    def test_activate_nonexistent_resume(self, client, db_session, test_user):
        """Test activating a resume that doesn't exist."""
        response = client.put(f"/resumes/{uuid4()}/activate")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestResumeDeletion:
    """Test the DELETE /resumes/{resume_id} endpoint."""

    def test_delete_resume(self, client, db_session, test_user):
        """Test deleting a resume."""
        resume = Resume(
            user_id=test_user.id,
            filename="to_delete.pdf",
            extracted_text="Content",
            content_hash="a" * 64,
            is_active=True
        )
        db_session.add(resume)
        db_session.commit()
        db_session.refresh(resume)
        resume_id = resume.id
        
        response = client.delete(f"/resumes/{resume_id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify deletion
        deleted = db_session.query(Resume).filter(Resume.id == resume_id).first()
        assert deleted is None

    def test_delete_inactive_resume(self, client, db_session, test_user):
        """Test deleting an inactive resume."""
        # Create active and inactive resumes
        resume1 = Resume(
            user_id=test_user.id,
            filename="active.pdf",
            extracted_text="Content 1",
            content_hash="a" * 64,
            is_active=True
        )
        resume2 = Resume(
            user_id=test_user.id,
            filename="inactive.pdf",
            extracted_text="Content 2",
            content_hash="b" * 64,
            is_active=False
        )
        db_session.add_all([resume1, resume2])
        db_session.commit()
        db_session.refresh(resume1)
        db_session.refresh(resume2)
        
        # Delete inactive resume
        response = client.delete(f"/resumes/{resume2.id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify resume1 is still active
        db_session.refresh(resume1)
        assert resume1.is_active is True

    def test_delete_active_resume_promotes_newest(self, client, db_session, test_user):
        """Test deleting the active resume promotes the newest remaining resume."""
        # Create multiple resumes, first is active
        resume1 = Resume(
            user_id=test_user.id,
            filename="resume1.pdf",
            extracted_text="Content 1",
            content_hash="a" * 64,
            is_active=True
        )
        resume2 = Resume(
            user_id=test_user.id,
            filename="resume2.pdf",
            extracted_text="Content 2",
            content_hash="b" * 64,
            is_active=False
        )
        db_session.add_all([resume1, resume2])
        db_session.commit()
        db_session.refresh(resume1)
        db_session.refresh(resume2)
        
        # Delete active resume
        response = client.delete(f"/resumes/{resume1.id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify resume2 is now active
        db_session.refresh(resume2)
        assert resume2.is_active is True

    def test_delete_nonexistent_resume(self, client, db_session, test_user):
        """Test deleting a resume that doesn't exist."""
        response = client.delete(f"/resumes/{uuid4()}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestResumeModelProperties:
    """Test the Resume model properties."""

    def test_extracted_text_length_property(self, db_session, test_user):
        """Test the extracted_text_length property."""
        text = "A" * 100
        resume = Resume(
            user_id=test_user.id,
            filename="test.pdf",
            extracted_text=text,
            content_hash="a" * 64,
            is_active=True
        )
        db_session.add(resume)
        db_session.commit()
        
        assert resume.extracted_text_length == 100

    def test_extracted_text_length_empty(self, db_session, test_user):
        """Test extracted_text_length with empty text."""
        resume = Resume(
            user_id=test_user.id,
            filename="empty.pdf",
            extracted_text="",
            content_hash="a" * 64,
            is_active=True
        )
        db_session.add(resume)
        db_session.commit()
        
        assert resume.extracted_text_length == 0

    def test_resume_version_property(self, db_session, test_user):
        """Test the resume_version property."""
        resume = Resume(
            user_id=test_user.id,
            filename="test.pdf",
            extracted_text="Content",
            content_hash="test_hash_123456",
            is_active=True
        )
        db_session.add(resume)
        db_session.commit()
        
        assert resume.resume_version == "test_hash_123456"


class TestResumeLimits:
    """Test resume storage limits."""

    def test_max_resumes_per_user_limit(self, client, db_session, test_user,
                                        pdf_bytes, mock_resume_analysis):
        """Test that users cannot exceed the maximum number of resumes."""
        # Create MAX_RESUMES_PER_USER (25) resumes
        for i in range(25):
            resume = Resume(
                user_id=test_user.id,
                filename=f"resume_{i}.pdf",
                extracted_text=f"Content {i}",
                # Unique, and 64 chars wide like a real SHA-256 hex digest
                content_hash=f"{i:064x}",
                is_active=(i == 0)
            )
            db_session.add(resume)
        db_session.commit()

        # Try to upload one more
        response = client.post(
            "/resumes/analyze",
            files={"file": ("resume_26.pdf", pdf_bytes)},
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "limit of 25" in response.json()["detail"]
        # Rejected before the AI is called, so a refused upload costs no quota
        mock_resume_analysis.assert_not_called()
