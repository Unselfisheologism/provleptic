# tests/test_compliance.py
"""Tests for DPDP compliance module."""

import pytest
from datetime import datetime, timedelta

from src.compliance.dpdp import (
    DPDPChecker,
    DataMinimizer,
    PurposeLimiter,
    RetentionPolicy,
    Purpose
)


class TestDataMinimizer:
    """Tests for DataMinimizer."""

    def test_minimize_policy_analysis(self):
        """Test data minimization for policy analysis purpose."""
        minimizer = DataMinimizer()
        
        data = {
            "district": "Nashik",
            "state": "Maharashtra",
            "name": "John Doe",  # PII
            "aadhaar": "123456789012",  # PII
            "pmay_utilization_percent": 45
        }
        
        result = minimizer.minimize(data, Purpose.POLICY_ANALYSIS)
        
        assert "district" in result
        assert "pmay_utilization_percent" in result
        assert "aadhaar" not in result
        assert "name" not in result

    def test_minimize_fund_utilization(self):
        """Test data minimization for fund utilization purpose."""
        minimizer = DataMinimizer()
        
        data = {
            "district": "Nashik",
            "funds_allocated": 1000000,
            "funds_utilized": 450000,
            "email": "test@example.com"
        }
        
        result = minimizer.minimize(data, Purpose.FUND_UTILIZATION)
        
        assert "district" in result
        assert "funds_allocated" in result
        assert "email" not in result

    def test_get_relevant_fields(self):
        """Test getting relevant fields for a purpose."""
        minimizer = DataMinimizer()
        
        fields = minimizer.get_relevant_fields(Purpose.POLICY_ANALYSIS)
        
        assert "district" in fields
        assert "utilization_percent" in fields


class TestPurposeLimiter:
    """Tests for PurposeLimiter."""

    def test_mark_purpose(self):
        """Test marking data with purpose."""
        limiter = PurposeLimiter()
        
        limiter.mark_purpose("data_123", Purpose.POLICY_ANALYSIS)
        
        assert limiter.get_purpose("data_123") == Purpose.POLICY_ANALYSIS

    def test_verify_purpose_match(self):
        """Test purpose verification when purposes match."""
        limiter = PurposeLimiter()
        
        limiter.mark_purpose("data_123", Purpose.POLICY_ANALYSIS)
        
        assert limiter.verify_purpose("data_123", Purpose.POLICY_ANALYSIS) is True

    def test_verify_purpose_mismatch(self):
        """Test purpose verification when purposes don't match."""
        limiter = PurposeLimiter()
        
        limiter.mark_purpose("data_123", Purpose.POLICY_ANALYSIS)
        
        assert limiter.verify_purpose("data_123", Purpose.FUND_UTILIZATION) is False

    def test_verify_purpose_unmarked(self):
        """Test verification for unmarked data."""
        limiter = PurposeLimiter()
        
        # Should allow if not marked (returns True for flexibility)
        assert limiter.verify_purpose("unknown_data", Purpose.POLICY_ANALYSIS) is True


class TestRetentionPolicy:
    """Tests for RetentionPolicy."""

    def test_create_entry(self):
        """Test creating retention entry."""
        policy = RetentionPolicy()
        
        entry = policy.create_entry("data_123", Purpose.POLICY_ANALYSIS)
        
        assert entry.data_id == "data_123"
        assert entry.purpose == Purpose.POLICY_ANALYSIS
        assert entry.retention_until is not None

    def test_should_delete_expired(self):
        """Test detection of expired data."""
        policy = RetentionPolicy({
            Purpose.POLICY_ANALYSIS: 0  # 0 days = immediate expiration
        })
        
        policy.create_entry("data_123", Purpose.POLICY_ANALYSIS)
        
        # Immediately should delete (0 days retention)
        assert policy.should_delete("data_123") is True

    def test_should_not_delete_within_retention(self):
        """Test that data within retention is not flagged for deletion."""
        policy = RetentionPolicy({
            Purpose.POLICY_ANALYSIS: 365  # 1 year
        })
        
        policy.create_entry("data_123", Purpose.POLICY_ANALYSIS)
        
        assert policy.should_delete("data_123") is False

    def test_mark_purpose_served(self):
        """Test marking purpose as served."""
        policy = RetentionPolicy()
        
        policy.create_entry("data_123", Purpose.PUBLIC_INQUIRY)
        policy.mark_purpose_served("data_123")
        
        assert policy.should_delete("data_123") is True

    def test_get_retention_info(self):
        """Test getting retention information."""
        policy = RetentionPolicy()
        
        policy.create_entry("data_123", Purpose.POLICY_ANALYSIS)
        
        info = policy.get_retention_info("data_123")
        
        assert info["data_id"] == "data_123"
        assert info["purpose"] == Purpose.POLICY_ANALYSIS.value
        assert "retention_until" in info


class TestDPDPChecker:
    """Tests for DPDPChecker."""

    @pytest.fixture
    def checker(self):
        """Create a DPDP checker instance."""
        return DPDPChecker()

    def test_minimize_data(self, checker):
        """Test complete data minimization flow."""
        data = {
            "district": "Nashik",
            "population": 6000000,
            "aadhaar": "123456789012",
            "pmay_utilization_percent": 45
        }
        
        result = checker.minimize_data(data, Purpose.DISTRICT_REVIEW, "data_123")
        
        assert "district" in result
        assert "pmay_utilization_percent" in result
        assert "aadhaar" not in result

    def test_verify_access(self, checker):
        """Test access verification."""
        checker.minimize_data(
            {"district": "Nashik"},
            Purpose.POLICY_ANALYSIS,
            "data_123"
        )
        
        assert checker.verify_access("data_123", Purpose.POLICY_ANALYSIS) is True
        assert checker.verify_access("data_123", Purpose.FUND_UTILIZATION) is False

    def test_check_retention(self, checker):
        """Test retention checking."""
        checker.minimize_data(
            {"district": "Nashik"},
            Purpose.PUBLIC_INQUIRY,
            "data_123"
        )
        
        # Within retention period should not be deleted
        assert checker.check_retention("data_123") is False

    def test_get_compliance_report(self, checker):
        """Test compliance report generation."""
        # Add some data
        checker.minimize_data(
            {"district": "Nashik", "pmay": 45},
            Purpose.POLICY_ANALYSIS,
            "data_1"
        )
        checker.minimize_data(
            {"district": "Pune", "pmay": 78},
            Purpose.FUND_UTILIZATION,
            "data_2"
        )
        
        report = checker.get_compliance_report(["data_1", "data_2"])
        
        assert report["total_checked"] == 2
        assert len(report["items"]) == 2