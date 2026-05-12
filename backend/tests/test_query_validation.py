"""
Tests for Query Parameter Validation with Pydantic

Validates that:
- Invalid pagination parameters return 422 (Unprocessable Entity)
- Search queries are properly validated
- Trip filters work correctly
- Date validation (ISO8601 format and range checking)
- MongoDB ObjectId validation
"""

import pytest
from datetime import date
from pydantic import ValidationError
from src.schemas.pagination import PaginationParams, TripFilters


class TestPaginationParamsValidation:
    """Test basic pagination parameter validation."""
    
    def test_valid_pagination_params(self):
        """Valid pagination params should parse successfully."""
        params = PaginationParams(page=1, limit=50)
        assert params.page == 1
        assert params.limit == 50
        assert params.q is None
    
    def test_default_pagination_params(self):
        """Pagination params should have sensible defaults."""
        params = PaginationParams()
        assert params.page == 1
        assert params.limit == 50
        assert params.q is None
    
    def test_page_minimum_boundary(self):
        """Page must be >= 1."""
        with pytest.raises(ValidationError):
            PaginationParams(page=0)
    
    def test_page_maximum_boundary(self):
        """Page must be <= 100."""
        with pytest.raises(ValidationError):
            PaginationParams(page=101)
    
    def test_limit_minimum_boundary(self):
        """Limit must be >= 1."""
        with pytest.raises(ValidationError):
            PaginationParams(limit=0)
    
    def test_limit_maximum_boundary(self):
        """Limit must be <= 100."""
        with pytest.raises(ValidationError):
            PaginationParams(limit=1000)


class TestSearchQueryValidation:
    """Test search query (q parameter) validation."""
    
    def test_valid_search_query(self):
        """Valid search queries should parse."""
        params = PaginationParams(q="search term")
        assert params.q == "search term"
    
    def test_search_query_none_allowed(self):
        """None/empty search query should be allowed."""
        params = PaginationParams(q=None)
        assert params.q is None
    
    def test_search_query_whitespace_trimmed(self):
        """Whitespace should be trimmed from search query."""
        params = PaginationParams(q="  search term  ")
        assert params.q == "search term"
    
    def test_search_query_empty_string_invalid(self):
        """Empty string should be invalid."""
        with pytest.raises(ValidationError):
            PaginationParams(q="")
    
    def test_search_query_whitespace_only_invalid(self):
        """Whitespace-only query should be invalid."""
        with pytest.raises(ValidationError):
            PaginationParams(q="   ")
    
    def test_search_query_minimum_length(self):
        """Search query must have minimum 1 character."""
        with pytest.raises(ValidationError):
            PaginationParams(q="")
    
    def test_search_query_maximum_length(self):
        """Search query must not exceed 100 characters."""
        long_query = "a" * 101
        with pytest.raises(ValidationError):
            PaginationParams(q=long_query)
    
    def test_search_query_at_max_boundary(self):
        """Search query at exactly 100 chars should be valid."""
        max_query = "a" * 100
        params = PaginationParams(q=max_query)
        assert len(params.q) == 100


class TestTripFiltersValidation:
    """Test trip-specific filter validation."""
    
    def test_valid_trip_filters(self):
        """Valid trip filters should parse."""
        filters = TripFilters(
            page=1,
            limit=50,
            status="completed",
            client_id="507f1f77bcf86cd799439011",
            vehicle_id="507f1f77bcf86cd799439012",
            driver_id="507f1f77bcf86cd799439013",
            from_date="2026-01-01",
            to_date="2026-12-31"
        )
        
        assert filters.page == 1
        assert filters.status == "completed"
        assert filters.from_date == "2026-01-01"
        assert filters.to_date == "2026-12-31"
    
    def test_trip_status_valid_values(self):
        """Trip status must be one of allowed values."""
        valid_statuses = ["pending", "in_transit", "completed", "cancelled"]
        
        for status in valid_statuses:
            filters = TripFilters(status=status)
            assert filters.status == status
    
    def test_trip_status_invalid_value(self):
        """Invalid trip status should be rejected."""
        with pytest.raises(ValidationError):
            TripFilters(status="invalid_status")
    
    def test_trip_status_none_allowed(self):
        """None trip status should be allowed."""
        filters = TripFilters(status=None)
        assert filters.status is None


class TestObjectIdValidation:
    """Test MongoDB ObjectId validation."""
    
    def test_valid_mongodb_object_id(self):
        """Valid MongoDB ObjectId should parse."""
        valid_id = "507f1f77bcf86cd799439011"
        filters = TripFilters(client_id=valid_id)
        assert filters.client_id == valid_id
    
    def test_invalid_mongodb_object_id_too_short(self):
        """ObjectId too short should be rejected."""
        with pytest.raises(ValidationError):
            TripFilters(client_id="507f1f77bcf86cd79943901")  # 23 chars
    
    def test_invalid_mongodb_object_id_too_long(self):
        """ObjectId too long should be rejected."""
        with pytest.raises(ValidationError):
            TripFilters(client_id="507f1f77bcf86cd7994390110")  # 25 chars
    
    def test_invalid_mongodb_object_id_non_hex(self):
        """ObjectId with non-hex characters should be rejected."""
        with pytest.raises(ValidationError):
            TripFilters(client_id="507f1f77bcf86cd799439G11")  # 'G' is not hex
    
    def test_mongodb_object_id_none_allowed(self):
        """None ObjectId should be allowed."""
        filters = TripFilters(client_id=None)
        assert filters.client_id is None
    
    def test_all_object_id_fields(self):
        """All ObjectId fields should validate the same way."""
        valid_id = "507f1f77bcf86cd799439011"
        
        filters = TripFilters(
            client_id=valid_id,
            vehicle_id=valid_id,
            driver_id=valid_id
        )
        
        assert filters.client_id == valid_id
        assert filters.vehicle_id == valid_id
        assert filters.driver_id == valid_id


class TestDateValidation:
    """Test date format and range validation."""
    
    def test_valid_iso8601_date(self):
        """Valid ISO8601 dates should parse."""
        filters = TripFilters(from_date="2026-01-15", to_date="2026-12-31")
        assert filters.from_date == "2026-01-15"
        assert filters.to_date == "2026-12-31"
    
    def test_invalid_date_format(self):
        """Invalid date format should be rejected."""
        invalid_dates = [
            "01-15-2026",  # MM-DD-YYYY
            "2026/01/15",  # Slash separator
            "2026-1-15",   # Missing leading zero
            "2026-01-5",   # Missing leading zero on day
            "01/15/2026",  # US format
            "15-01-2026",  # DD-MM-YYYY
            "2026-13-01",  # Invalid month
            "2026-01-32",  # Invalid day
        ]
        
        for invalid_date in invalid_dates:
            with pytest.raises(ValidationError):
                TripFilters(from_date=invalid_date)
    
    def test_date_range_validation(self):
        """from_date must be <= to_date."""
        with pytest.raises(ValidationError) as exc_info:
            TripFilters(from_date="2026-12-31", to_date="2026-01-01")
        
        assert "from_date must be less than or equal to to_date" in str(exc_info.value)
    
    def test_equal_dates_allowed(self):
        """Equal from_date and to_date should be allowed."""
        filters = TripFilters(from_date="2026-06-15", to_date="2026-06-15")
        assert filters.from_date == "2026-06-15"
        assert filters.to_date == "2026-06-15"
    
    def test_date_none_allowed(self):
        """None dates should be allowed."""
        filters = TripFilters(from_date=None, to_date=None)
        assert filters.from_date is None
        assert filters.to_date is None
    
    def test_only_from_date(self):
        """Only from_date can be specified."""
        filters = TripFilters(from_date="2026-01-01", to_date=None)
        assert filters.from_date == "2026-01-01"
        assert filters.to_date is None
    
    def test_only_to_date(self):
        """Only to_date can be specified."""
        filters = TripFilters(from_date=None, to_date="2026-12-31")
        assert filters.from_date is None
        assert filters.to_date == "2026-12-31"


class TestTripFiltersIntegration:
    """Integration tests for complete trip filters."""
    
    def test_complex_trip_filter_query(self):
        """Complex trip filter with multiple parameters should work."""
        filters = TripFilters(
            page=2,
            limit=25,
            q="partial delivery",
            status="in_transit",
            client_id="507f1f77bcf86cd799439011",
            vehicle_id="507f1f77bcf86cd799439012",
            from_date="2026-04-01",
            to_date="2026-04-30"
        )
        
        assert filters.page == 2
        assert filters.limit == 25
        assert filters.q == "partial delivery"
        assert filters.status == "in_transit"
        assert filters.from_date == "2026-04-01"
    
    def test_minimal_trip_filter(self):
        """Trip filter with only defaults should work."""
        filters = TripFilters()
        assert filters.page == 1
        assert filters.limit == 50
        assert filters.q is None
        assert filters.status is None
    
    def test_trip_filter_with_search_only(self):
        """Trip filter with only search query should work."""
        filters = TripFilters(q="urgent pickup")
        assert filters.page == 1
        assert filters.q == "urgent pickup"
        assert filters.status is None
    
    def test_trip_filter_with_date_range_only(self):
        """Trip filter with only date range should work."""
        filters = TripFilters(
            from_date="2026-03-01",
            to_date="2026-03-31"
        )
        assert filters.from_date == "2026-03-01"
        assert filters.to_date == "2026-03-31"


class TestPaginationParamsFromDict:
    """Test creating models from dictionary (simulating request.args)."""
    
    def test_create_from_empty_dict(self):
        """Creating from empty dict should use defaults."""
        params = PaginationParams(**{})
        assert params.page == 1
        assert params.limit == 50
    
    def test_create_from_partial_dict(self):
        """Creating from partial dict should fill in defaults."""
        params = PaginationParams(**{"page": 2})
        assert params.page == 2
        assert params.limit == 50
    
    def test_create_from_full_dict(self):
        """Creating from full dict should use all values."""
        data = {"page": 3, "limit": 75, "q": "test"}
        params = PaginationParams(**data)
        assert params.page == 3
        assert params.limit == 75
        assert params.q == "test"
    
    def test_invalid_type_conversion(self):
        """Invalid types should raise validation errors."""
        # page as string that can't convert to int
        with pytest.raises(ValidationError):
            PaginationParams(**{"page": "invalid"})
