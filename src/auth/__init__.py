# src/auth/__init__.py
from .simulator import RoleSimulator, get_current_role, require_role

__all__ = ['RoleSimulator', 'get_current_role', 'require_role']