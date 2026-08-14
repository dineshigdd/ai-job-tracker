"""Test cases for helper functions used in job search and filter."""
import pytest
from app.routers.jobs import _escape_like


class TestEscapeLikeFunction:
    """Test the _escape_like helper function for SQL LIKE pattern escaping."""

    def test_escape_percent_sign(self):
        """Test that % is escaped as \\%."""
        assert _escape_like("100%") == "100\\%"

    def test_escape_underscore(self):
        """Test that _ is escaped as \\_."""
        assert _escape_like("test_value") == "test\\_value"

    def test_escape_backslash(self):
        """Test that backslash is escaped as \\\\."""
        assert _escape_like("test\\value") == "test\\\\value"

    def test_escape_multiple_special_chars(self):
        """Test escaping multiple special characters."""
        assert _escape_like("100%_test\\value") == "100\\%\\_test\\\\value"

    def test_no_special_chars(self):
        """Test that normal strings are unchanged."""
        assert _escape_like("normal string") == "normal string"

    def test_empty_string(self):
        """Test empty string."""
        assert _escape_like("") == ""
