# Test Cases for Job Search & Filter Feature

This directory contains comprehensive test cases for the **Search & Filter** functionality of the `/jobs` endpoint.

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
└── test_edge_cases.py       # Edge case tests
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
| test_search_filter.py | 21 | Search and filter tests |
| test_pagination.py | 7 | Pagination tests |
| test_sorting.py | 5 | Sorting tests |
| test_response.py | 3 | Response structure tests |
| test_edge_cases.py | 4 | Edge case tests |
| **Total** | **48** | All tests |
