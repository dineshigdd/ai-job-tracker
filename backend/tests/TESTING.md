# Backend API Tests

This directory contains comprehensive test cases for the **FastAPI backend**, covering the `/jobs` endpoint with search, filter, pagination, sorting, authentication, and response validation.

## Test File Structure

The tests are organized into **logical modules** by functionality:

```
tests/
├── __init__.py              # Python package init
├── conftest.py              # Pytest fixtures (shared across all test files)
├── test_helpers.py          # Helper function tests
├── test_auth.py             # Authentication & authorization tests
├── test_search_filter.py    # Search and filter functionality tests
├── test_pagination.py        # Pagination tests
├── test_sorting.py          # Sorting tests
├── test_response.py         # API response structure tests
├── test_edge_cases.py       # Edge case tests
├── test_ai_service.py       # AI service (cover letter, resume analysis) tests
├── test_match_score.py      # ATS match scoring algorithm tests
├── test_match_score_api.py  # Match score API endpoint tests
└── test_resumes.py          # Resume upload, storage, and management tests
```

## Running Tests

### Prerequisites
```bash
pip install -r requirements-test.txt
```

### Run All Tests
```bash
pytest tests/
```

### Run Specific Module
```bash
pytest tests/test_search_filter.py
```

### Run Specific Class
```bash
pytest tests/test_search_filter.py::TestStatusFilter
```

### Run Specific Test
```bash
pytest tests/test_search_filter.py::TestStatusFilter::test_filter_by_status_applied
```

### Run with Coverage
```bash
pytest tests/ --cov=app --cov-report=term-missing
```

## Test Statistics

| Module | Tests | Description |
|--------|-------|-------------|
| test_helpers.py | 6 | Helper function tests |
| test_auth.py | 2 | Authentication tests |
| test_search_filter.py | 23 | Search and filter tests |
| test_pagination.py | 8 | Pagination tests |
| test_sorting.py | 5 | Sorting tests |
| test_response.py | 3 | Response structure tests |
| test_edge_cases.py | 4 | Edge case tests |
| test_ai_service.py | 28 | AI service (cover letter, resume analysis) tests |
| test_match_score.py | 40 | ATS match scoring algorithm tests |
| test_match_score_api.py | 26 | Match score API endpoint tests |
| test_resumes.py | 32 | Resume upload, storage, and management tests |
| **Total** | **177** | All tests |
