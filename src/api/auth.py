"""Authentication and authorization utilities."""

import time
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from src.api.exceptions import ForbiddenError, UnauthorizedError

# API Key authentication scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# OAuth 2.0 Bearer token authentication scheme
bearer_scheme = HTTPBearer(auto_error=False)


class AuthService:
    """Authentication service for validating API keys and tokens."""

    def __init__(self) -> None:
        """Initialize authentication service."""
        # TODO: Load API keys and tokens from secure storage (e.g., HashiCorp Vault)
        # This is a placeholder implementation
        self.valid_api_keys = {
            "test-api-key-123": {"client_id": "test-client", "permissions": ["read", "write"]},
        }
        self.valid_tokens = {
            "test-bearer-token-456": {
                "user_id": "test-user",
                "roles": ["Process_Engineer"],
                "permissions": ["read", "write", "admin"],
            },
        }

    def validate_api_key(self, api_key: str) -> dict:
        """
        Validate API key and return client information.

        Args:
            api_key: API key to validate

        Returns:
            Client information dictionary

        Raises:
            UnauthorizedError: If API key is invalid
        """
        if api_key not in self.valid_api_keys:
            raise UnauthorizedError("Invalid API key")
        return self.valid_api_keys[api_key]

    def validate_bearer_token(self, token: str) -> dict:
        """
        Validate OAuth 2.0 bearer token and return user information.

        Args:
            token: Bearer token to validate

        Returns:
            User information dictionary

        Raises:
            UnauthorizedError: If token is invalid
        """
        if token not in self.valid_tokens:
            raise UnauthorizedError("Invalid bearer token")
        return self.valid_tokens[token]

    def check_permission(self, user_info: dict, required_permission: str) -> None:
        """
        Check if user has required permission.

        Args:
            user_info: User information dictionary
            required_permission: Required permission

        Raises:
            ForbiddenError: If user lacks required permission
        """
        permissions = user_info.get("permissions", [])
        if required_permission not in permissions:
            raise ForbiddenError(
                f"Insufficient permissions. Required: {required_permission}"
            )


# Global auth service instance
auth_service = AuthService()


async def get_current_user(
    api_key: Optional[str] = Depends(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    """
    Get current authenticated user from API key or bearer token.

    Supports both API key authentication (X-API-Key header) and
    OAuth 2.0 bearer token authentication (Authorization: Bearer header).

    Args:
        api_key: API key from X-API-Key header
        bearer: Bearer token from Authorization header

    Returns:
        User/client information dictionary

    Raises:
        UnauthorizedError: If no valid authentication provided
    """
    # Try API key authentication first
    if api_key:
        return auth_service.validate_api_key(api_key)

    # Try bearer token authentication
    if bearer:
        return auth_service.validate_bearer_token(bearer.credentials)

    # No valid authentication provided
    raise UnauthorizedError("Authentication required. Provide X-API-Key or Authorization header.")


async def require_permission(permission: str):
    """
    Dependency factory for requiring specific permissions.

    Args:
        permission: Required permission

    Returns:
        Dependency function that checks permission
    """

    async def permission_checker(user: dict = Depends(get_current_user)) -> dict:
        """Check if user has required permission."""
        auth_service.check_permission(user, permission)
        return user

    return permission_checker
