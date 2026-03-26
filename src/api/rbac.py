"""Role-based access control (RBAC) implementation."""

import logging
from functools import wraps
from typing import Any, Callable, Dict, List

from fastapi import Depends

from src.api.exceptions import ForbiddenError
from src.api.keycloak_auth import (
    Permission,
    Role,
    ROLE_PERMISSIONS,
    get_current_user,
    require_permission,
    require_role,
)

logger = logging.getLogger(__name__)


class RBACService:
    """Role-based access control service."""

    def __init__(self) -> None:
        """Initialize RBAC service."""
        self.role_permissions = ROLE_PERMISSIONS

    def get_permissions_for_role(self, role: str) -> List[str]:
        """
        Get permissions for a role.

        Args:
            role: Role name

        Returns:
            List of permissions
        """
        return self.role_permissions.get(role, [])

    def get_permissions_for_roles(self, roles: List[str]) -> List[str]:
        """
        Get combined permissions for multiple roles.

        Args:
            roles: List of role names

        Returns:
            List of unique permissions
        """
        permissions = set()
        for role in roles:
            permissions.update(self.get_permissions_for_role(role))
        return list(permissions)

    def has_permission(self, user: Dict[str, Any], permission: str) -> bool:
        """
        Check if user has specific permission.

        Args:
            user: User information dictionary
            permission: Permission to check

        Returns:
            True if user has permission
        """
        user_permissions = user.get("permissions", [])
        return permission in user_permissions

    def has_role(self, user: Dict[str, Any], role: str) -> bool:
        """
        Check if user has specific role.

        Args:
            user: User information dictionary
            role: Role to check

        Returns:
            True if user has role
        """
        user_roles = user.get("roles", [])
        return role in user_roles

    def has_any_role(self, user: Dict[str, Any], roles: List[str]) -> bool:
        """
        Check if user has any of the specified roles.

        Args:
            user: User information dictionary
            roles: List of roles to check

        Returns:
            True if user has at least one role
        """
        user_roles = user.get("roles", [])
        return any(role in user_roles for role in roles)

    def has_all_roles(self, user: Dict[str, Any], roles: List[str]) -> bool:
        """
        Check if user has all of the specified roles.

        Args:
            user: User information dictionary
            roles: List of roles to check

        Returns:
            True if user has all roles
        """
        user_roles = user.get("roles", [])
        return all(role in user_roles for role in roles)

    def check_permission(self, user: Dict[str, Any], permission: str) -> None:
        """
        Check permission and raise exception if not authorized.

        Args:
            user: User information dictionary
            permission: Required permission

        Raises:
            ForbiddenError: If user lacks permission
        """
        if not self.has_permission(user, permission):
            logger.warning(
                f"Permission denied for user {user.get('username')}: "
                f"required={permission}, has={user.get('permissions', [])}"
            )
            raise ForbiddenError(f"Insufficient permissions. Required: {permission}")

    def check_role(self, user: Dict[str, Any], role: str) -> None:
        """
        Check role and raise exception if not authorized.

        Args:
            user: User information dictionary
            role: Required role

        Raises:
            ForbiddenError: If user lacks role
        """
        if not self.has_role(user, role):
            logger.warning(
                f"Role check failed for user {user.get('username')}: "
                f"required={role}, has={user.get('roles', [])}"
            )
            raise ForbiddenError(f"Insufficient role. Required: {role}")


# Global RBAC service
rbac_service = RBACService()


# Convenience dependencies for common permission checks

async def require_view_model(user: dict = Depends(get_current_user)) -> dict:
    """Require view_model permission."""
    rbac_service.check_permission(user, Permission.VIEW_MODEL)
    return user


async def require_edit_model(user: dict = Depends(get_current_user)) -> dict:
    """Require edit_model permission."""
    rbac_service.check_permission(user, Permission.EDIT_MODEL)
    return user


async def require_create_model(user: dict = Depends(get_current_user)) -> dict:
    """Require create_model permission."""
    rbac_service.check_permission(user, Permission.CREATE_MODEL)
    return user


async def require_delete_model(user: dict = Depends(get_current_user)) -> dict:
    """Require delete_model permission."""
    rbac_service.check_permission(user, Permission.DELETE_MODEL)
    return user


async def require_run_simulation(user: dict = Depends(get_current_user)) -> dict:
    """Require run_simulation permission."""
    rbac_service.check_permission(user, Permission.RUN_SIMULATION)
    return user


async def require_view_rca(user: dict = Depends(get_current_user)) -> dict:
    """Require view_rca permission."""
    rbac_service.check_permission(user, Permission.VIEW_RCA)
    return user


async def require_view_reports(user: dict = Depends(get_current_user)) -> dict:
    """Require view_reports permission."""
    rbac_service.check_permission(user, Permission.VIEW_REPORTS)
    return user


async def require_configure_alerts(user: dict = Depends(get_current_user)) -> dict:
    """Require configure_alerts permission."""
    rbac_service.check_permission(user, Permission.CONFIGURE_ALERTS)
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Require admin permission."""
    rbac_service.check_permission(user, Permission.ADMIN)
    return user


# Role-specific dependencies

async def require_process_engineer(user: dict = Depends(get_current_user)) -> dict:
    """Require Process_Engineer role."""
    rbac_service.check_role(user, Role.PROCESS_ENGINEER)
    return user


async def require_plant_manager(user: dict = Depends(get_current_user)) -> dict:
    """Require Plant_Manager role."""
    rbac_service.check_role(user, Role.PLANT_MANAGER)
    return user


async def require_qa_lead(user: dict = Depends(get_current_user)) -> dict:
    """Require QA_Lead role."""
    rbac_service.check_role(user, Role.QA_LEAD)
    return user


async def require_citizen_data_scientist(user: dict = Depends(get_current_user)) -> dict:
    """Require Citizen_Data_Scientist role."""
    rbac_service.check_role(user, Role.CITIZEN_DATA_SCIENTIST)
    return user
