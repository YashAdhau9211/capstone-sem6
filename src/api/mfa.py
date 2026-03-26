"""Multi-factor authentication service."""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional

import pyotp
from pydantic import BaseModel

from config.settings import settings

logger = logging.getLogger(__name__)


class MFAMethod:
    """MFA method types."""

    TOTP = "totp"
    SMS = "sms"
    HARDWARE_TOKEN = "hardware_token"


class MFAConfig(BaseModel):
    """MFA configuration for a user."""

    user_id: str
    method: str
    enabled: bool
    secret: Optional[str] = None  # For TOTP
    phone_number: Optional[str] = None  # For SMS
    backup_codes: list[str] = []


class MFAService:
    """Multi-factor authentication service."""

    def __init__(self) -> None:
        """Initialize MFA service."""
        # In-memory storage for demo (use database in production)
        self.mfa_configs: Dict[str, MFAConfig] = {}
        self.pending_verifications: Dict[str, Dict] = {}

    def setup_totp(self, user_id: str, username: str) -> Dict[str, str]:
        """
        Set up TOTP-based MFA for user.

        Args:
            user_id: User identifier
            username: Username for display

        Returns:
            Dictionary with secret and provisioning URI
        """
        # Generate secret
        secret = pyotp.random_base32()

        # Create TOTP instance
        totp = pyotp.TOTP(secret)

        # Generate provisioning URI for QR code
        provisioning_uri = totp.provisioning_uri(
            name=username, issuer_name="Causal AI Platform"
        )

        # Generate backup codes
        backup_codes = [secrets.token_hex(4) for _ in range(10)]

        # Store configuration (not enabled until verified)
        self.mfa_configs[user_id] = MFAConfig(
            user_id=user_id,
            method=MFAMethod.TOTP,
            enabled=False,
            secret=secret,
            backup_codes=backup_codes,
        )

        return {
            "secret": secret,
            "provisioning_uri": provisioning_uri,
            "backup_codes": backup_codes,
        }

    def verify_totp(self, user_id: str, code: str) -> bool:
        """
        Verify TOTP code.

        Args:
            user_id: User identifier
            code: TOTP code to verify

        Returns:
            True if code is valid
        """
        if user_id not in self.mfa_configs:
            return False

        config = self.mfa_configs[user_id]
        if config.method != MFAMethod.TOTP or not config.secret:
            return False

        # Check backup codes first
        if code in config.backup_codes:
            # Remove used backup code
            config.backup_codes.remove(code)
            logger.info(f"Backup code used for user {user_id}")
            return True

        # Verify TOTP code
        totp = pyotp.TOTP(config.secret)
        is_valid = totp.verify(code, valid_window=1)  # Allow 1 time step tolerance

        return is_valid

    def enable_mfa(self, user_id: str, verification_code: str) -> bool:
        """
        Enable MFA after successful verification.

        Args:
            user_id: User identifier
            verification_code: Code to verify

        Returns:
            True if MFA was enabled

        Raises:
            ValueError: If verification fails
        """
        if not self.verify_totp(user_id, verification_code):
            raise ValueError("Invalid verification code")

        if user_id in self.mfa_configs:
            self.mfa_configs[user_id].enabled = True
            logger.info(f"MFA enabled for user {user_id}")
            return True

        return False

    def disable_mfa(self, user_id: str) -> None:
        """
        Disable MFA for user.

        Args:
            user_id: User identifier
        """
        if user_id in self.mfa_configs:
            self.mfa_configs[user_id].enabled = False
            logger.info(f"MFA disabled for user {user_id}")

    def is_mfa_enabled(self, user_id: str) -> bool:
        """
        Check if MFA is enabled for user.

        Args:
            user_id: User identifier

        Returns:
            True if MFA is enabled
        """
        if user_id not in self.mfa_configs:
            return False
        return self.mfa_configs[user_id].enabled

    def get_mfa_config(self, user_id: str) -> Optional[MFAConfig]:
        """
        Get MFA configuration for user.

        Args:
            user_id: User identifier

        Returns:
            MFA configuration or None
        """
        return self.mfa_configs.get(user_id)

    def setup_sms(self, user_id: str, phone_number: str) -> Dict[str, str]:
        """
        Set up SMS-based MFA for user.

        Args:
            user_id: User identifier
            phone_number: Phone number for SMS

        Returns:
            Dictionary with setup information
        """
        # Generate backup codes
        backup_codes = [secrets.token_hex(4) for _ in range(10)]

        # Store configuration
        self.mfa_configs[user_id] = MFAConfig(
            user_id=user_id,
            method=MFAMethod.SMS,
            enabled=False,
            phone_number=phone_number,
            backup_codes=backup_codes,
        )

        # Send verification SMS (implementation depends on SMS provider)
        verification_code = secrets.token_hex(3)
        self.pending_verifications[user_id] = {
            "code": verification_code,
            "expires_at": datetime.utcnow() + timedelta(minutes=5),
        }

        logger.info(f"SMS MFA setup initiated for user {user_id}")

        return {
            "phone_number": phone_number,
            "backup_codes": backup_codes,
            "verification_code": verification_code,  # Remove in production
        }

    def verify_sms(self, user_id: str, code: str) -> bool:
        """
        Verify SMS code.

        Args:
            user_id: User identifier
            code: SMS code to verify

        Returns:
            True if code is valid
        """
        if user_id not in self.pending_verifications:
            return False

        verification = self.pending_verifications[user_id]
        if datetime.utcnow() > verification["expires_at"]:
            del self.pending_verifications[user_id]
            return False

        if code == verification["code"]:
            del self.pending_verifications[user_id]
            return True

        return False


# Global MFA service
mfa_service = MFAService()


class PasswordPolicy:
    """Password policy enforcement."""

    @staticmethod
    def validate_password(password: str) -> None:
        """
        Validate password against policy.

        Args:
            password: Password to validate

        Raises:
            ValueError: If password doesn't meet requirements
        """
        if len(password) < settings.password_min_length:
            raise ValueError(
                f"Password must be at least {settings.password_min_length} characters"
            )

        # Check complexity requirements
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        if not (has_upper and has_lower and has_digit and has_special):
            raise ValueError(
                "Password must contain uppercase, lowercase, digit, and special character"
            )
