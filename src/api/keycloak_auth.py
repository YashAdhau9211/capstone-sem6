"""Keycloak authentication and authorization service."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import jwt
import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from config.settings import settings
from src.api.exceptions import ForbiddenError, UnauthorizedError

logger = logging.getLogger(__name__)

# Bearer token authentication scheme
bearer_scheme = HTTPBearer(auto_error=False)


class Role:
    """Role definitions."""

    PROCESS_ENGINEER = "Process_Engineer"
    PLANT_MANAGER = "Plant_Manager"
    QA_LEAD = "QA_Lead"
    CITIZEN_DATA_SCIENTIST = "Citizen_Data_Scientist"
    ADMIN = "Admin"


class Permission:
    """Permission definitions."""

    VIEW_MODEL = "view_model"
    EDIT_MODEL = "edit_model"
    CREATE_MODEL = "create_model"
    DELETE_MODEL = "delete_model"
    RUN_SIMULATION = "run_simulation"
    VIEW_RCA = "view_rca"
    VIEW_REPORTS = "view_reports"
    CONFIGURE_ALERTS = "configure_alerts"
    ADMIN = "admin"


# Role-to-permissions mapping
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    Role.PROCESS_ENGINEER: [
        Permission.VIEW_MODEL,
        Permission.EDIT_MODEL,
        Permission.CREATE_MODEL,
        Permission.DELETE_MODEL,
        Permission.RUN_SIMULATION,
        Permission.VIEW_RCA,
    ],
    Role.PLANT_MANAGER: [
        Permission.VIEW_MODEL,
        Permission.RUN_SIMULATION,
        Permission.VIEW_RCA,
        Permission.VIEW_REPORTS,
    ],
    Role.QA_LEAD: [
        Permission.VIEW_MODEL,
        Permission.VIEW_RCA,
        Permission.CONFIGURE_ALERTS,
    ],
    Role.CITIZEN_DATA_SCIENTIST: [
        Permission.RUN_SIMULATION,
        Permission.VIEW_MODEL,
    ],
    Role.ADMIN: [
        Permission.VIEW_MODEL,
        Permission.EDIT_MODEL,
        Permission.CREATE_MODEL,
        Permission.DELETE_MODEL,
        Permission.RUN_SIMULATION,
        Permission.VIEW_RCA,
        Permission.VIEW_REPORTS,
        Permission.CONFIGURE_ALERTS,
        Permission.ADMIN,
    ],
}


class SessionManager:
    """Manage user sessions with timeout tracking."""

    def __init__(self) -> None:
        """Initialize session manager."""
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.failed_login_attempts: Dict[str, List[datetime]] = {}

    def create_session(self, user_id: str, user_data: Dict[str, Any]) -> str:
        """
        Create a new session for user.

        Args:
            user_id: User identifier
            user_data: User information

        Returns:
            Session ID
        """
        session_id = f"session-{user_id}-{int(datetime.utcnow().timestamp())}"
        self.sessions[session_id] = {
            "user_id": user_id,
            "user_data": user_data,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
        }
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data if valid.

        Args:
            session_id: Session identifier

        Returns:
            Session data or None if expired/invalid
        """
        if session_id not in self.sessions:
            return None

        session = self.sessions[session_id]
        last_activity = session["last_activity"]
        timeout = timedelta(minutes=settings.session_timeout_minutes)

        if datetime.utcnow() - last_activity > timeout:
            # Session expired
            del self.sessions[session_id]
            return None

        # Update last activity
        session["last_activity"] = datetime.utcnow()
        return session

    def delete_session(self, session_id: str) -> None:
        """
        Delete a session.

        Args:
            session_id: Session identifier
        """
        if session_id in self.sessions:
            del self.sessions[session_id]

    def record_failed_login(self, username: str) -> bool:
        """
        Record a failed login attempt.

        Args:
            username: Username that failed login

        Returns:
            True if account should be locked
        """
        now = datetime.utcnow()
        if username not in self.failed_login_attempts:
            self.failed_login_attempts[username] = []

        # Remove old attempts outside lockout window
        lockout_duration = timedelta(minutes=settings.account_lockout_duration_minutes)
        self.failed_login_attempts[username] = [
            attempt
            for attempt in self.failed_login_attempts[username]
            if now - attempt < lockout_duration
        ]

        # Add new attempt
        self.failed_login_attempts[username].append(now)

        # Check if should lock
        return len(self.failed_login_attempts[username]) >= settings.max_failed_login_attempts

    def is_account_locked(self, username: str) -> bool:
        """
        Check if account is locked due to failed login attempts.

        Args:
            username: Username to check

        Returns:
            True if account is locked
        """
        if username not in self.failed_login_attempts:
            return False

        now = datetime.utcnow()
        lockout_duration = timedelta(minutes=settings.account_lockout_duration_minutes)

        # Remove old attempts
        self.failed_login_attempts[username] = [
            attempt
            for attempt in self.failed_login_attempts[username]
            if now - attempt < lockout_duration
        ]

        return len(self.failed_login_attempts[username]) >= settings.max_failed_login_attempts

    def clear_failed_attempts(self, username: str) -> None:
        """
        Clear failed login attempts for user.

        Args:
            username: Username to clear
        """
        if username in self.failed_login_attempts:
            del self.failed_login_attempts[username]


# Global session manager
session_manager = SessionManager()


class KeycloakAuthService:
    """Keycloak authentication service."""

    def __init__(self) -> None:
        """Initialize Keycloak auth service."""
        self.keycloak_url = settings.keycloak_url
        self.realm = settings.keycloak_realm
        self.client_id = settings.keycloak_client_id
        self.client_secret = settings.keycloak_client_secret

        # JWK client for token validation
        jwks_url = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/certs"
        self.jwks_client = PyJWKClient(jwks_url)

    def get_token_endpoint(self) -> str:
        """Get Keycloak token endpoint URL."""
        return f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token"

    def get_userinfo_endpoint(self) -> str:
        """Get Keycloak userinfo endpoint URL."""
        return f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/userinfo"

    def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user with Keycloak.

        Args:
            username: Username
            password: Password

        Returns:
            Token response from Keycloak

        Raises:
            UnauthorizedError: If authentication fails
        """
        # Check if account is locked
        if session_manager.is_account_locked(username):
            logger.warning(f"Login attempt for locked account: {username}")
            raise UnauthorizedError(
                f"Account locked due to too many failed attempts. "
                f"Try again in {settings.account_lockout_duration_minutes} minutes."
            )

        try:
            response = requests.post(
                self.get_token_endpoint(),
                data={
                    "grant_type": "password",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "username": username,
                    "password": password,
                },
                timeout=10,
            )

            if response.status_code != 200:
                # Record failed attempt
                should_lock = session_manager.record_failed_login(username)
                if should_lock:
                    logger.warning(f"Account locked due to failed attempts: {username}")
                    raise UnauthorizedError(
                        f"Account locked due to too many failed attempts. "
                        f"Try again in {settings.account_lockout_duration_minutes} minutes."
                    )
                raise UnauthorizedError("Invalid username or password")

            # Clear failed attempts on successful login
            session_manager.clear_failed_attempts(username)

            return response.json()

        except requests.RequestException as e:
            logger.error(f"Keycloak authentication error: {e}")
            raise UnauthorizedError("Authentication service unavailable")

    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate JWT token from Keycloak.

        Args:
            token: JWT access token

        Returns:
            Decoded token payload

        Raises:
            UnauthorizedError: If token is invalid
        """
        try:
            # Get signing key from JWKS
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)

            # Decode and validate token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=[settings.jwt_algorithm],
                audience=self.client_id,
                options={"verify_exp": True},
            )

            return payload

        except jwt.ExpiredSignatureError:
            raise UnauthorizedError("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {e}")
            raise UnauthorizedError("Invalid token")
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise UnauthorizedError("Token validation failed")

    def get_user_info(self, token: str) -> Dict[str, Any]:
        """
        Get user information from Keycloak.

        Args:
            token: Access token

        Returns:
            User information

        Raises:
            UnauthorizedError: If request fails
        """
        try:
            response = requests.get(
                self.get_userinfo_endpoint(),
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )

            if response.status_code != 200:
                raise UnauthorizedError("Failed to get user info")

            return response.json()

        except requests.RequestException as e:
            logger.error(f"Keycloak userinfo error: {e}")
            raise UnauthorizedError("Failed to get user info")

    def extract_roles(self, token_payload: Dict[str, Any]) -> List[str]:
        """
        Extract roles from token payload.

        Args:
            token_payload: Decoded JWT payload

        Returns:
            List of role names
        """
        roles = []

        # Extract realm roles
        if "realm_access" in token_payload:
            roles.extend(token_payload["realm_access"].get("roles", []))

        # Extract client roles
        if "resource_access" in token_payload:
            client_access = token_payload["resource_access"].get(self.client_id, {})
            roles.extend(client_access.get("roles", []))

        return roles

    def get_permissions_for_roles(self, roles: List[str]) -> List[str]:
        """
        Get permissions for given roles.

        Args:
            roles: List of role names

        Returns:
            List of permissions
        """
        permissions = set()
        for role in roles:
            if role in ROLE_PERMISSIONS:
                permissions.update(ROLE_PERMISSIONS[role])
        return list(permissions)


# Global Keycloak auth service
keycloak_service = KeycloakAuthService()


async def get_current_user(
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Dict[str, Any]:
    """
    Get current authenticated user from JWT token.

    Args:
        bearer: Bearer token from Authorization header

    Returns:
        User information dictionary with roles and permissions

    Raises:
        UnauthorizedError: If no valid authentication provided
    """
    if not bearer:
        raise UnauthorizedError("Authentication required. Provide Authorization header.")

    # Validate token
    token_payload = keycloak_service.validate_token(bearer.credentials)

    # Extract user information
    user_id = token_payload.get("sub")
    username = token_payload.get("preferred_username")
    email = token_payload.get("email")

    # Extract roles
    roles = keycloak_service.extract_roles(token_payload)

    # Get permissions
    permissions = keycloak_service.get_permissions_for_roles(roles)

    return {
        "user_id": user_id,
        "username": username,
        "email": email,
        "roles": roles,
        "permissions": permissions,
        "token_payload": token_payload,
    }


def require_permission(permission: str):
    """
    Dependency factory for requiring specific permissions.

    Args:
        permission: Required permission

    Returns:
        Dependency function that checks permission
    """

    async def permission_checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        """Check if user has required permission."""
        permissions = user.get("permissions", [])
        if permission not in permissions:
            logger.warning(
                f"Permission denied for user {user.get('username')}: "
                f"required={permission}, has={permissions}"
            )
            raise ForbiddenError(f"Insufficient permissions. Required: {permission}")
        return user

    return permission_checker


def require_role(role: str):
    """
    Dependency factory for requiring specific role.

    Args:
        role: Required role

    Returns:
        Dependency function that checks role
    """

    async def role_checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        """Check if user has required role."""
        roles = user.get("roles", [])
        if role not in roles:
            logger.warning(
                f"Role check failed for user {user.get('username')}: "
                f"required={role}, has={roles}"
            )
            raise ForbiddenError(f"Insufficient role. Required: {role}")
        return user

    return role_checker
