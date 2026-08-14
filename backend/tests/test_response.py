"""Test cases for response structure in job search."""
import pytest
from fastapi import status


class TestResponseStructure:
    """Test the structure of the API response."""

    def test_response_has_required_fields(self, client, create_test_jobs):
        """Test that response includes all required fields."""
        response = client.get("/jobs/")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["limit"], int)
        assert isinstance(data["offset"], int)

    def test_job_items_have_required_fields(self, client, create_test_jobs):
        """Test that each job item has all required fields."""
        response = client.get("/jobs/")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        for job in data["items"]:
            assert "id" in job
            assert "company_name" in job
            assert "job_title" in job
            assert "status" in job
            assert "user_id" in job

    def test_total_reflects_filtered_count(self, client, create_test_jobs):
        """Test that total count reflects the filtered results."""
        response = client.get("/jobs/?status=Applied")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["total"] == 3  # 3 Applied jobs
        assert len(data["items"]) <= data["limit"]
