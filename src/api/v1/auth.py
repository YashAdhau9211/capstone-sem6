"""Authentication endpoints."""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, status
from pydantic import BaseModel

from src.api.exceptions import UnauthorizedError
from src.api.keycloak_auth import (
    Permission,
    Role,
    get_current_user,
    keycloak_service,
    require_permission,
    session_manager,
)
from src.api.mfa import MFAConfig, mfa_service, PasswordPolicy

logger = logging.getLogger(__name__)
router = APIRouter()


class LoginResponse(BaseModel):
    """Login response model."""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    user: dict
    mfa_required: bool = False
    mfa_token: Optional[str] = None


class MFASetupResponse(BaseModel):
    """MFA setup response model."""

    method: str
    secret: Optional[str] = None
    provisioning_uri: Optional[str] = None
    phone_number: Optional[str] = None
    backup_codes: list[str]


class User(BaseModel):
    """User model."""

    user_id: str
    username: str
    email: Optional[str] = None
    roles: list[str]
    permissions: list[str]


@router.post("/login", response_model=LoginResponse)
async def login(
    username: str = Form(...),
    password: str = Form(...),
) -> LoginResponse:
    """
    Login endpoint for username/password authentication.

    Args:
        username: Username
        password: Password

    Returns:
        LoginResponse with access token and user information

    Raises:
        HTTPException: If credentials are invalid
    """
    try:
        # Authenticate with Keycloak
        token_response = keycloak_service.authenticate(username, password)

        # Validate token and get user info
        token_payload = keycloak_service.validate_token(token_response["access_token"])

        # Extract user information
        user_id = token_payload.get("sub")
        email = token_payload.get("email")
        roles = keycloak_service.extract_roles(token_payload)
        permissions = keycloak_service.get_permissions_for_roles(roles)

        user_data = {
            "user_id": user_id,
            "username": username,
            "email": email,
            "roles": roles,
            "permissions": permissions,
        }

        # Check if MFA is enabled
        mfa_enabled = mfa_service.is_mfa_enabled(user_id)

        if mfa_enabled:
            # Create temporary session for MFA verification
            mfa_token = session_manager.create_session(user_id, user_data)
            logger.info(f"MFA required for user {username}")

            return LoginResponse(
                access_token="",
                token_type="bearer",
                expires_in=0,
                user=user_data,
                mfa_required=True,
                mfa_token=mfa_token,
            )

        # Create session
        session_id = session_manager.create_session(user_id, user_data)

        logger.info(f"User logged in: {username}")

        return LoginResponse(
            access_token=token_response["access_token"],
            refresh_token=token_response.get("refresh_token"),
            token_type="bearer",
            expires_in=token_response.get("expires_in", 300),
            user=user_data,
            mfa_required=False,
        )

    except UnauthorizedError as e:
        logger.warning(f"Login failed for user {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Login error for user {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error",
        )


@router.post("/mfa/verify")
async def verify_mfa(
    mfa_token: str = Form(...),
    code: str = Form(...),
) -> LoginResponse:
    """
    Verify MFA code and complete login.

    Args:
        mfa_token: Temporary MFA token from login
        code: MFA verification code

    Returns:
        LoginResponse with access token

    Raises:
        HTTPException: If verification fails
    """
    # Get session
    session = session_manager.get_session(mfa_token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired MFA token",
        )

    user_id = session["user_id"]
    user_data = session["user_data"]

    # Verify MFA code
    if not mfa_service.verify_totp(user_id, code):
        logger.warning(f"MFA verification failed for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code",
        )

    # Delete temporary MFA session
    session_manager.delete_session(mfa_token)

    # Re-authenticate to get fresh token
    try:
        # Note: In production, you'd need to store credentials securely or use refresh token
        # For now, we'll create a session-based token
        session_id = session_manager.create_session(user_id, user_data)

        logger.info(f"MFA verification successful for user {user_data['username']}")

        return LoginResponse(
            access_token=session_id,  # Use session ID as token for demo
            token_type="bearer",
            expires_in=1800,  # 30 minutes
            user=user_data,
            mfa_required=False,
        )

    except Exception as e:
        logger.error(f"MFA verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MFA verification error",
        )


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)) -> dict:
    """
    Logout endpoint.

    Args:
        user: Current authenticated user

    Returns:
        Success message
    """
    logger.info(f"User logged out: {user.get('username')}")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=User)
async def get_current_user_info(user: dict = Depends(get_current_user)) -> User:
    """
    Get current user information.

    Args:
        user: Current authenticated user

    Returns:
        User information
    """
    return User(
        user_id=user["user_id"],
        username=user["username"],
        email=user.get("email"),
        roles=user["roles"],
        permissions=user["permissions"],
    )


@router.post("/mfa/setup/totp", response_model=MFASetupResponse)
async def setup_totp_mfa(user: dict = Depends(get_current_user)) -> MFASetupResponse:
    """
    Set up TOTP-based MFA for current user.

    Args:
        user: Current authenticated user

    Returns:
        MFA setup information with secret and QR code URI
    """
    user_id = user["user_id"]
    username = user["username"]

    setup_data = mfa_service.setup_totp(user_id, username)

    logger.info(f"TOTP MFA setup initiated for user {username}")

    return MFASetupResponse(
        method="totp",
        secret=setup_data["secret"],
        provisioning_uri=setup_data["provisioning_uri"],
        backup_codes=setup_data["backup_codes"],
    )


@router.post("/mfa/setup/sms", response_model=MFASetupResponse)
async def setup_sms_mfa(
    phone_number: str = Form(...),
    user: dict = Depends(get_current_user),
) -> MFASetupResponse:
    """
    Set up SMS-based MFA for current user.

    Args:
        phone_number: Phone number for SMS
        user: Current authenticated user

    Returns:
        MFA setup information
    """
    user_id = user["user_id"]

    setup_data = mfa_service.setup_sms(user_id, phone_number)

    logger.info(f"SMS MFA setup initiated for user {user['username']}")

    return MFASetupResponse(
        method="sms",
        phone_number=setup_data["phone_number"],
        backup_codes=setup_data["backup_codes"],
    )


@router.post("/mfa/enable")
async def enable_mfa(
    verification_code: str = Form(...),
    user: dict = Depends(get_current_user),
) -> dict:
    """
    Enable MFA after successful verification.

    Args:
        verification_code: Verification code
        user: Current authenticated user

    Returns:
        Success message

    Raises:
        HTTPException: If verification fails
    """
    user_id = user["user_id"]

    try:
        mfa_service.enable_mfa(user_id, verification_code)
        logger.info(f"MFA enabled for user {user['username']}")
        return {"message": "MFA enabled successfully"}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/mfa/disable")
async def disable_mfa(user: dict = Depends(get_current_user)) -> dict:
    """
    Disable MFA for current user.

    Args:
        user: Current authenticated user

    Returns:
        Success message
    """
    user_id = user["user_id"]
    mfa_service.disable_mfa(user_id)

    logger.info(f"MFA disabled for user {user['username']}")

    return {"message": "MFA disabled successfully"}


@router.get("/mfa/status")
async def get_mfa_status(user: dict = Depends(get_current_user)) -> dict:
    """
    Get MFA status for current user.

    Args:
        user: Current authenticated user

    Returns:
        MFA status information
    """
    user_id = user["user_id"]
    config = mfa_service.get_mfa_config(user_id)

    if not config:
        return {
            "enabled": False,
            "method": None,
        }

    return {
        "enabled": config.enabled,
        "method": config.method,
        "backup_codes_remaining": len(config.backup_codes),
    }


@router.post("/password/validate")
async def validate_password(password: str = Form(...)) -> dict:
    """
    Validate password against policy.

    Args:
        password: Password to validate

    Returns:
        Validation result

    Raises:
        HTTPException: If password doesn't meet requirements
    """
    try:
        PasswordPolicy.validate_password(password)
        return {"valid": True, "message": "Password meets requirements"}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

