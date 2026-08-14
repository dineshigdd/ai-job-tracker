"""Test cases for authentication and authorization in job search."""
import pytest
from fastapi import status
from app.models import JobStatus


class TestAuthenticationAndAuthorization:
    """Test authentication and multi-tenancy security."""

    def test_get_jobs_requires_authentication(self):
        """Verify that unauthenticated requests are rejected with 401."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        # Create a client without auth overrides
        with TestClient(app) as unauth_client:
            response = unauth_client.get("/jobs/")
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_can_only_see_own_jobs(self, client, db_session):
        """Verify that users can only see their own job applications."""
        from app.models import User, Job
        from uuid import uuid4
        
        # Create a second user with a job
        other_user = User(
            id=uuid4(),
            email="other@example.com",
            hashed_password="hashed_password"
        )
        db_session.add(other_user)
        db_session.commit()
        
        other_job = Job(
            user_id=other_user.id,
            company_name="Other Company",
            job_title="Other Job",
            status=JobStatus.APPLIED
        )
        db_session.add(other_job)
        db_session.commit()
        
        # Authenticated user (created by test_user fixture) should not see other user's job
        response = client.get("/jobs/")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        job_ids = [str(job["id"]) for job in data["items"]]
        # Convert other_job.id to string for comparison
        assert str(other_job.id) not in job_ids
