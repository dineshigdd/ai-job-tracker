"""Test cases for pagination in job search."""
import pytest
from fastapi import status


class TestPagination:
    """Test pagination parameters (limit and offset)."""

    def test_default_pagination(self, client, create_test_jobs):
        """Test default pagination (limit=50, offset=0)."""
        response = client.get("/jobs/")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["limit"] == 50
        assert data["offset"] == 0
        assert len(data["items"]) == 9  # All jobs fit in default limit

    def test_custom_limit(self, client, create_test_jobs):
        """Test custom limit parameter."""
        response = client.get("/jobs/?limit=3")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 3
        assert data["limit"] == 3
        assert data["total"] == 9  # Total is independent of limit

    def test_custom_offset(self, client, create_test_jobs):
        """Test custom offset parameter."""
        response = client.get("/jobs/?limit=3&offset=3")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 3
        assert data["offset"] == 3

    def test_pagination_with_filters(self, client, create_test_jobs):
        """Test pagination works correctly with filters applied."""
        response = client.get("/jobs/?status=Applied&limit=2")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 3  # 3 Applied jobs total

    def test_offset_beyond_total(self, client, create_test_jobs):
        """Test offset beyond total number of jobs returns empty list."""
        response = client.get("/jobs/?offset=100")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 0
        assert data["offset"] == 100

    def test_invalid_limit_low(self, client):
        """Test that limit < 1 is rejected."""
        response = client.get("/jobs/?limit=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_limit_high(self, client):
        """Test that limit > 100 is rejected."""
        response = client.get("/jobs/?limit=101")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_offset_negative(self, client):
        """Test that offset < 0 is rejected."""
        response = client.get("/jobs/?offset=-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
