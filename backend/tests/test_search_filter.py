"""Test cases for search and filter functionality in job search."""
import pytest
from fastapi import status
from app.models import JobStatus


class TestStatusFilter:
    """Test filtering by status parameter."""

    def test_filter_by_status_applied(self, client, create_test_jobs):
        """Test filtering jobs by Applied status."""
        response = client.get("/jobs/?status=Applied")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 3  # Google, Amazon, Senior Solutions
        for job in data["items"]:
            assert job["status"] == "Applied"

    def test_filter_by_status_interviewing(self, client, create_test_jobs):
        """Test filtering jobs by Interviewing status."""
        response = client.get("/jobs/?status=Interviewing")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 3  # Microsoft, Apple, Anthropic
        for job in data["items"]:
            assert job["status"] == "Interviewing"

    def test_filter_by_status_offer(self, client, create_test_jobs):
        """Test filtering jobs by Offer status."""
        response = client.get("/jobs/?status=Offer")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 1  # Meta
        assert data["items"][0]["status"] == "Offer"

    def test_filter_by_status_rejected(self, client, create_test_jobs):
        """Test filtering jobs by Rejected status."""
        response = client.get("/jobs/?status=Rejected")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 1  # Netflix
        assert data["items"][0]["status"] == "Rejected"

    def test_filter_by_status_wishlist(self, client, create_test_jobs):
        """Test filtering jobs by Wishlist status."""
        response = client.get("/jobs/?status=Wishlist")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 1  # Google Frontend
        assert data["items"][0]["status"] == "Wishlist"

    def test_filter_by_nonexistent_status(self, client):
        """Test that invalid status values are rejected with 422."""
        response = client.get("/jobs/?status=InvalidStatus")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_no_status_filter_returns_all(self, client, create_test_jobs):
        """Test that omitting status filter returns all jobs."""
        response = client.get("/jobs/")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 9  # All test jobs (Google x2, Microsoft, Amazon, Meta, Netflix, Apple, Senior Solutions, Anthropic)


class TestSearchKeyword:
    """Test searching by keyword across company_name and job_title."""

    def test_search_exact_company_name_match(self, client, create_test_jobs):
        """Test exact match on company name."""
        response = client.get("/jobs/?search=Google")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        # Should match both Google jobs
        assert len(data["items"]) == 2
        for job in data["items"]:
            assert "Google" in job["company_name"]

    def test_search_exact_title_match(self, client, create_test_jobs):
        """Test exact match on job title."""
        response = client.get("/jobs/?search=Data Engineer")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["job_title"] == "Data Engineer"

    def test_search_partial_match_company(self, client, create_test_jobs):
        """Test partial string match on company name."""
        response = client.get("/jobs/?search=Goog")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 2  # Both Google jobs

    def test_search_partial_match_title(self, client, create_test_jobs):
        """Test partial string match on job title."""
        response = client.get("/jobs/?search=Engineer")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        # Should match: Senior Backend Engineer, Software Engineer, Frontend Engineer, Data Engineer
        assert len(data["items"]) >= 4

    def test_search_case_insensitive(self, client, create_test_jobs):
        """Test that search is case-insensitive."""
        # Lowercase
        response1 = client.get("/jobs/?search=google")
        assert response1.status_code == status.HTTP_200_OK
        assert len(response1.json()["items"]) == 2
        
        # Uppercase
        response2 = client.get("/jobs/?search=GOOGLE")
        assert response2.status_code == status.HTTP_200_OK
        assert len(response2.json()["items"]) == 2
        
        # Mixed case
        response3 = client.get("/jobs/?search=GoOgLe")
        assert response3.status_code == status.HTTP_200_OK
        assert len(response3.json()["items"]) == 2

    def test_search_matches_both_company_and_title(self, client, create_test_jobs):
        """Test that search matches across both company_name and job_title."""
        response = client.get("/jobs/?search=Senior")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        # Should match: Senior Backend Engineer, Senior Engineer, Senior Solutions
        assert len(data["items"]) == 3

    def test_search_empty_string(self, client, create_test_jobs):
        """Test that empty search string returns all jobs."""
        response = client.get("/jobs/?search=")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 9  # All jobs (Google x2, Microsoft, Amazon, Meta, Netflix, Apple, Senior Solutions, Anthropic)

    def test_search_whitespace_only(self, client, create_test_jobs):
        """Test that whitespace-only search string returns all jobs."""
        response = client.get("/jobs/?search=   ")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 9  # All jobs (Google x2, Microsoft, Amazon, Meta, Netflix, Apple, Senior Solutions, Anthropic)

    def test_search_no_results(self, client, create_test_jobs):
        """Test that search with no matches returns empty list."""
        response = client.get("/jobs/?search=NonExistentCompany123")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 0
        assert data["total"] == 0

    def test_search_max_length(self, client, create_test_jobs):
        """Test that search strings longer than MAX_SEARCH_LENGTH (100) are rejected."""
        long_search = "a" * 101
        response = client.get(f"/jobs/?search={long_search}")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestSpecialCharacterSearch:
    """Test handling of special characters in search (LIKE wildcards)."""

    def test_search_with_percent_sign(self, client, create_special_char_jobs):
        """Test that literal % signs are escaped and not treated as wildcards."""
        response = client.get("/jobs/?search=100% Remote")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        # Should match only the exact company "100% Remote"
        assert len(data["items"]) == 1
        assert data["items"][0]["company_name"] == "100% Remote"

    def test_search_with_underscore(self, client, create_special_char_jobs):
        """Test that literal _ characters are escaped and not treated as wildcards."""
        response = client.get("/jobs/?search=Company_A")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        # Should match only the exact company "Company_A"
        assert len(data["items"]) == 1
        assert data["items"][0]["company_name"] == "Company_A"

    def test_search_with_backslash(self, client, create_special_char_jobs):
        """Test that backslashes are properly escaped."""
        response = client.get("/jobs/?search=Test\\Backslash")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        # Should match only the exact company "Test\Backslash"
        assert len(data["items"]) == 1
        assert data["items"][0]["company_name"] == "Test\\Backslash"


class TestCombinedFilters:
    """Test combining status and search filters."""

    def test_status_and_search_combined(self, client, create_test_jobs):
        """Test that status and search filters are AND-ed together."""
        # Search for Interviewing jobs at Anthropic
        # Anthropic has status=Interviewing in the test data
        response = client.get("/jobs/?status=Interviewing&search=Anthropic")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        # Should match only: Anthropic - Backend Engineer (Interviewing)
        assert len(data["items"]) == 1
        assert data["items"][0]["company_name"] == "Anthropic"
        assert data["items"][0]["status"] == "Interviewing"

    def test_status_and_search_no_match(self, client, create_test_jobs):
        """Test combined filters with no matching results."""
        # Search for Offer jobs at Google (none exist - Google has Applied/Wishlist, Meta has Offer)
        response = client.get("/jobs/?status=Offer&search=Google")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 0
        assert data["total"] == 0

    def test_multiple_search_terms_not_supported(self, client, create_test_jobs):
        """Test that searching for multiple terms (space-separated) is treated as a single pattern."""
        # This searches for the literal string "Backend Engineer" (not AND/OR)
        response = client.get("/jobs/?search=Backend Engineer")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        # Should match jobs where company_name or job_title contains "Backend Engineer"
        # Only "Senior Backend Engineer" matches this exact phrase in title
        matching_jobs = [j for j in data["items"] if "Backend Engineer" in j["job_title"]]
        assert len(matching_jobs) >= 1
