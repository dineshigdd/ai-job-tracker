"""Test cases for edge cases in job search."""
import pytest
from fastapi import status


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_database(self, client, db_session):
        """Test behavior when user has no jobs."""
        # Each test gets a unique user with no jobs by default
        response = client.get("/jobs/")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 0
        assert data["total"] == 0

    def test_all_jobs_filtered_out(self, client, create_test_jobs):
        """Test behavior when filters exclude all jobs."""
        response = client.get("/jobs/?status=Offer&search=NonExistent")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 0
        assert data["total"] == 0

    def test_status_filter_with_search_whitespace(self, client, create_test_jobs):
        """Test status filter combined with whitespace search."""
        response = client.get("/jobs/?status=Applied&search=   ")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        # Should return all Applied jobs (search is ignored)
        assert data["total"] == 3

    def test_multiple_parameters_order_independence(self, client, create_test_jobs):
        """Test that parameter order doesn't affect results."""
        response1 = client.get("/jobs/?status=Applied&search=Google&limit=10")
        response2 = client.get("/jobs/?search=Google&limit=10&status=Applied")
        response3 = client.get("/jobs/?limit=10&status=Applied&search=Google")
        
        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK
        assert response3.status_code == status.HTTP_200_OK
        
        data1 = response1.json()
        data2 = response2.json()
        data3 = response3.json()
        
        # All should return the same results
        assert len(data1["items"]) == len(data2["items"]) == len(data3["items"])
        assert data1["total"] == data2["total"] == data3["total"]
