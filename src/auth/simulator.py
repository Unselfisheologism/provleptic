# src/auth/simulator.py
"""Mock role-based access control simulator with JWT-like token support."""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from functools import wraps


class Role(Enum):
    """Available roles in the system."""
    ANALYST = "analyst"
    FIELD_OFFICER = "field_officer"
    POLICYMAKER = "policymaker"
    ADMIN = "admin"


@dataclass
class TokenPayload:
    """JWT-like token payload."""
    sub: str  # Subject (user ID)
    role: str
    exp: str  # Expiration timestamp
    iat: str  # Issued at timestamp
    permissions: List[str]
    session_id: str


class RoleSimulator:
    """
    Simulates role-based access control with JWT-like tokens.
    
    This is a mock implementation for demonstration purposes.
    In production, use proper JWT libraries and authentication systems.
    """

    # Role permissions mapping
    ROLE_PERMISSIONS = {
        Role.ANALYST: [
            "query:read",
            "ontology:read",
            "visualization:read",
            "rules:read",
        ],
        Role.FIELD_OFFICER: [
            "query:read",
            "ontology:read",
            "visualization:read",
            "rules:read",
            "rules:flag",
            "recommendation:request",
            "report:create",
        ],
        Role.POLICYMAKER: [
            "query:read",
            "ontology:read",
            "visualization:read",
            "rules:read",
            "rules:flag",
            "recommendation:request",
            "report:create",
            "report:export",
            "audit:read",
        ],
        Role.ADMIN: [
            "query:read",
            "query:write",
            "ontology:read",
            "ontology:write",
            "visualization:read",
            "rules:read",
            "rules:write",
            "rules:flag",
            "recommendation:request",
            "report:create",
            "report:export",
            "audit:read",
            "audit:write",
            "config:read",
            "config:write",
        ],
    }

    def __init__(self):
        self.tokens: Dict[str, TokenPayload] = {}
        self.sessions: Dict[str, Dict] = {}

    def generate_token(self, user_id: str, role: str, session_duration_hours: int = 24) -> str:
        """
        Generate a mock JWT-like token for a user.
        
        Args:
            user_id: Unique user identifier
            role: User role (analyst, field_officer, policymaker, admin)
            session_duration_hours: Token validity duration
        
        Returns:
            Mock token string (base64 encoded JSON + signature)
        """
        if role not in [r.value for r in Role]:
            raise ValueError(f"Invalid role: {role}")
        
        role_enum = Role(role)
        now = datetime.utcnow()
        expiration = now + timedelta(hours=session_duration_hours)
        
        # Create session ID
        session_id = hashlib.sha256(f"{user_id}{now.isoformat()}".encode()).hexdigest()[:16]
        
        payload = TokenPayload(
            sub=user_id,
            role=role,
            exp=expiration.isoformat(),
            iat=now.isoformat(),
            permissions=self.ROLE_PERMISSIONS[role_enum],
            session_id=session_id,
        )
        
        # Store token
        self.tokens[session_id] = payload
        self.sessions[session_id] = {
            "user_id": user_id,
            "role": role,
            "created_at": now.isoformat(),
        }
        
        # Create mock JWT (header.payload.signature)
        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = self._base64_encode(json.dumps(header))
        payload_json = json.dumps(asdict(payload))
        payload_b64 = self._base64_encode(payload_json)
        signature = self._sign(f"{header_b64}.{payload_b64}")
        
        return f"{header_b64}.{payload_b64}.{signature}"

    def verify_token(self, token: str) -> Optional[TokenPayload]:
        """
        Verify a mock JWT-like token.
        
        Args:
            token: The token string to verify
        
        Returns:
            TokenPayload if valid, None otherwise
        """
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            
            header_b64, payload_b64, signature = parts
            
            # Verify signature
            expected_sig = self._sign(f"{header_b64}.{payload_b64}")
            if signature != expected_sig:
                return None
            
            # Decode payload
            payload_json = self._base64_decode(payload_b64)
            payload_dict = json.loads(payload_json)
            
            # Check expiration
            exp = datetime.fromisoformat(payload_dict["exp"])
            if datetime.utcnow() > exp:
                return None
            
            # Retrieve from storage
            session_id = payload_dict.get("session_id")
            if session_id in self.tokens:
                return self.tokens[session_id]
            
            return TokenPayload(**payload_dict)
            
        except Exception:
            return None

    def get_role_permissions(self, role: str) -> List[str]:
        """Get permissions for a given role."""
        try:
            return self.ROLE_PERMISSIONS[Role(role)]
        except KeyError:
            return []

    def has_permission(self, token: str, permission: str) -> bool:
        """Check if token holder has a specific permission."""
        payload = self.verify_token(token)
        if not payload:
            return False
        return permission in payload.permissions

    def get_role_display_name(self, role: str) -> str:
        """Get human-readable role name."""
        role_names = {
            "analyst": "Data Analyst",
            "field_officer": "Field Officer",
            "policymaker": "Policymaker",
            "admin": "Administrator",
        }
        return role_names.get(role, role.title())

    def _base64_encode(self, data: str) -> str:
        """Mock base64 encoding."""
        import base64
        return base64.urlsafe_b64encode(data.encode()).decode().rstrip("=")

    def _base64_decode(self, data: str) -> str:
        """Mock base64 decoding."""
        import base64
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        return base64.urlsafe_b64decode(data.encode()).decode()

    def _sign(self, data: str) -> str:
        """Mock signature generation."""
        return hashlib.sha256(data.encode()).hexdigest()[:32]


# Global simulator instance
role_simulator = RoleSimulator()


def get_current_role() -> str:
    """Get the current role from streamlit session state or return default."""
    try:
        import streamlit as st
        return st.session_state.get("user_role", Role.ANALYST.value)
    except:
        return Role.ANALYST.value


def require_role(*allowed_roles: str):
    """Decorator to check if current user has required role."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current = get_current_role()
            if current not in allowed_roles:
                raise PermissionError(
                    f"Role '{current}' not authorized. Required: {allowed_roles}"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


def can_export(user_role: str) -> bool:
    """Check if user role can export reports."""
    return user_role in [Role.POLICYMAKER.value, Role.ADMIN.value]


def can_view_audit(user_role: str) -> bool:
    """Check if user role can view audit logs."""
    return user_role in [Role.POLICYMAKER.value, Role.ADMIN.value]


def can_flag_for_review(user_role: str) -> bool:
    """Check if user role can flag items for review."""
    return user_role in [Role.FIELD_OFFICER.value, Role.POLICYMAKER.value, Role.ADMIN.value]