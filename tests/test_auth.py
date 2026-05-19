# tests/test_auth.py
"""Tests for role-based access simulation."""

import pytest

from src.auth.simulator import (
    RoleSimulator,
    Role,
    can_export,
    can_view_audit,
    can_flag_for_review
)


class TestRoleSimulator:
    """Tests for RoleSimulator."""

    @pytest.fixture
    def simulator(self):
        """Create a simulator instance."""
        return RoleSimulator()

    def test_generate_token(self, simulator):
        """Test token generation."""
        token = simulator.generate_token("user_123", "analyst")
        
        assert token is not None
        assert len(token.split(".")) == 3  # header.payload.signature

    def test_verify_token(self, simulator):
        """Test token verification."""
        token = simulator.generate_token("user_123", "analyst")
        
        payload = simulator.verify_token(token)
        
        assert payload is not None
        assert payload.sub == "user_123"
        assert payload.role == "analyst"

    def test_verify_invalid_token(self, simulator):
        """Test verification of invalid token."""
        result = simulator.verify_token("invalid.token.here")
        
        assert result is None

    def test_verify_tampered_token(self, simulator):
        """Test verification of tampered token."""
        token = simulator.generate_token("user_123", "analyst")
        
        # Tamper with the token
        parts = token.split(".")
        parts[1] = "tampered" + parts[1]
        tampered = ".".join(parts)
        
        result = simulator.verify_token(tampered)
        
        assert result is None

    def test_get_role_permissions(self, simulator):
        """Test getting permissions for a role."""
        permissions = simulator.get_role_permissions("analyst")
        
        assert "query:read" in permissions
        assert "ontology:read" in permissions
        assert "report:export" not in permissions  # Analyst cannot export

    def test_has_permission(self, simulator):
        """Test permission checking."""
        token = simulator.generate_token("user_123", "analyst")
        
        assert simulator.has_permission(token, "query:read") is True
        assert simulator.has_permission(token, "report:export") is False

    def test_get_role_display_name(self, simulator):
        """Test getting human-readable role name."""
        assert simulator.get_role_display_name("analyst") == "Data Analyst"
        assert simulator.get_role_display_name("policymaker") == "Policymaker"
        assert simulator.get_role_display_name("field_officer") == "Field Officer"

    def test_invalid_role(self, simulator):
        """Test generating token with invalid role."""
        with pytest.raises(ValueError):
            simulator.generate_token("user_123", "superuser")


class TestRoleHelpers:
    """Tests for role helper functions."""

    def test_can_export(self):
        """Test export permission check."""
        assert can_export("policymaker") is True
        assert can_export("admin") is True
        assert can_export("analyst") is False
        assert can_export("field_officer") is False

    def test_can_view_audit(self):
        """Test audit view permission check."""
        assert can_view_audit("policymaker") is True
        assert can_view_audit("admin") is True
        assert can_view_audit("analyst") is False
        assert can_view_audit("field_officer") is False

    def test_can_flag_for_review(self):
        """Test flag for review permission check."""
        assert can_flag_for_review("policymaker") is True
        assert can_flag_for_review("field_officer") is True
        assert can_flag_for_review("admin") is True
        assert can_flag_for_review("analyst") is False