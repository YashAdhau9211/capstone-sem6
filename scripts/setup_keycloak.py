"""Script to configure Keycloak realm, clients, and roles."""

import logging
import sys
import time
from typing import Any, Dict, List

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Keycloak configuration
KEYCLOAK_URL = "http://localhost:8080"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
REALM_NAME = "causal-ai"
CLIENT_ID = "causal-ai-platform"

# Role definitions
ROLES = [
    {
        "name": "Process_Engineer",
        "description": "Process engineers who create and manage causal models",
    },
    {
        "name": "Plant_Manager",
        "description": "Plant managers who view models and reports",
    },
    {
        "name": "QA_Lead",
        "description": "QA leads who view RCA reports and configure alerts",
    },
    {
        "name": "Citizen_Data_Scientist",
        "description": "Citizen data scientists who run simulations",
    },
    {
        "name": "Admin",
        "description": "System administrators with full access",
    },
]

# Test users
TEST_USERS = [
    {
        "username": "engineer",
        "email": "engineer@example.com",
        "firstName": "Process",
        "lastName": "Engineer",
        "password": "Engineer123!",
        "roles": ["Process_Engineer"],
    },
    {
        "username": "manager",
        "email": "manager@example.com",
        "firstName": "Plant",
        "lastName": "Manager",
        "password": "Manager123!",
        "roles": ["Plant_Manager"],
    },
    {
        "username": "qa",
        "email": "qa@example.com",
        "firstName": "QA",
        "lastName": "Lead",
        "password": "QALead123!",
        "roles": ["QA_Lead"],
    },
    {
        "username": "analyst",
        "email": "analyst@example.com",
        "firstName": "Citizen",
        "lastName": "Analyst",
        "password": "Analyst123!",
        "roles": ["Citizen_Data_Scientist"],
    },
    {
        "username": "admin",
        "email": "admin@example.com",
        "firstName": "System",
        "lastName": "Admin",
        "password": "Admin123!",
        "roles": ["Admin"],
    },
]


class KeycloakSetup:
    """Keycloak setup utility."""

    def __init__(self) -> None:
        """Initialize Keycloak setup."""
        self.base_url = KEYCLOAK_URL
        self.admin_token: Optional[str] = None

    def wait_for_keycloak(self, max_retries: int = 30) -> None:
        """Wait for Keycloak to be ready."""
        logger.info("Waiting for Keycloak to be ready...")
        for i in range(max_retries):
            try:
                response = requests.get(f"{self.base_url}/health/ready", timeout=5)
                if response.status_code == 200:
                    logger.info("Keycloak is ready")
                    return
            except requests.RequestException:
                pass

            time.sleep(2)
            logger.info(f"Retry {i + 1}/{max_retries}...")

        raise RuntimeError("Keycloak did not become ready in time")

    def get_admin_token(self) -> str:
        """Get admin access token."""
        if self.admin_token:
            return self.admin_token

        logger.info("Getting admin token...")
        response = requests.post(
            f"{self.base_url}/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": ADMIN_USERNAME,
                "password": ADMIN_PASSWORD,
            },
            timeout=10,
        )

        if response.status_code != 200:
            raise RuntimeError(f"Failed to get admin token: {response.text}")

        self.admin_token = response.json()["access_token"]
        return self.admin_token

    def create_realm(self) -> None:
        """Create Keycloak realm."""
        logger.info(f"Creating realm: {REALM_NAME}")

        headers = {"Authorization": f"Bearer {self.get_admin_token()}"}

        # Check if realm exists
        response = requests.get(
            f"{self.base_url}/admin/realms/{REALM_NAME}",
            headers=headers,
            timeout=10,
        )

        if response.status_code == 200:
            logger.info(f"Realm {REALM_NAME} already exists")
            return

        # Create realm
        realm_config = {
            "realm": REALM_NAME,
            "enabled": True,
            "displayName": "Causal AI Manufacturing Platform",
            "accessTokenLifespan": 1800,  # 30 minutes
            "ssoSessionIdleTimeout": 1800,  # 30 minutes
            "ssoSessionMaxLifespan": 36000,  # 10 hours
            "passwordPolicy": (
                f"length({ADMIN_PASSWORD}MIN_LENGTH) and "
                "upperCase(1) and lowerCase(1) and digits(1) and specialChars(1)"
            ),
        }

        response = requests.post(
            f"{self.base_url}/admin/realms",
            headers={**headers, "Content-Type": "application/json"},
            json=realm_config,
            timeout=10,
        )

        if response.status_code not in [201, 409]:
            raise RuntimeError(f"Failed to create realm: {response.text}")

        logger.info(f"Realm {REALM_NAME} created successfully")

    def create_client(self) -> str:
        """Create Keycloak client."""
        logger.info(f"Creating client: {CLIENT_ID}")

        headers = {
            "Authorization": f"Bearer {self.get_admin_token()}",
            "Content-Type": "application/json",
        }

        # Check if client exists
        response = requests.get(
            f"{self.base_url}/admin/realms/{REALM_NAME}/clients",
            headers=headers,
            params={"clientId": CLIENT_ID},
            timeout=10,
        )

        if response.status_code == 200 and response.json():
            client_id = response.json()[0]["id"]
            logger.info(f"Client {CLIENT_ID} already exists")
            return client_id

        # Create client
        client_config = {
            "clientId": CLIENT_ID,
            "enabled": True,
            "publicClient": False,
            "directAccessGrantsEnabled": True,
            "serviceAccountsEnabled": True,
            "authorizationServicesEnabled": True,
            "standardFlowEnabled": True,
            "implicitFlowEnabled": False,
            "redirectUris": ["http://localhost:3000/*", "http://localhost:8000/*"],
            "webOrigins": ["http://localhost:3000", "http://localhost:8000"],
        }

        response = requests.post(
            f"{self.base_url}/admin/realms/{REALM_NAME}/clients",
            headers=headers,
            json=client_config,
            timeout=10,
        )

        if response.status_code != 201:
            raise RuntimeError(f"Failed to create client: {response.text}")

        # Get client ID
        response = requests.get(
            f"{self.base_url}/admin/realms/{REALM_NAME}/clients",
            headers=headers,
            params={"clientId": CLIENT_ID},
            timeout=10,
        )

        client_id = response.json()[0]["id"]
        logger.info(f"Client {CLIENT_ID} created successfully")
        return client_id

    def create_roles(self) -> None:
        """Create realm roles."""
        logger.info("Creating roles...")

        headers = {
            "Authorization": f"Bearer {self.get_admin_token()}",
            "Content-Type": "application/json",
        }

        for role in ROLES:
            # Check if role exists
            response = requests.get(
                f"{self.base_url}/admin/realms/{REALM_NAME}/roles/{role['name']}",
                headers=headers,
                timeout=10,
            )

            if response.status_code == 200:
                logger.info(f"Role {role['name']} already exists")
                continue

            # Create role
            response = requests.post(
                f"{self.base_url}/admin/realms/{REALM_NAME}/roles",
                headers=headers,
                json=role,
                timeout=10,
            )

            if response.status_code not in [201, 409]:
                logger.error(f"Failed to create role {role['name']}: {response.text}")
            else:
                logger.info(f"Role {role['name']} created successfully")

    def create_test_users(self) -> None:
        """Create test users with assigned roles."""
        logger.info("Creating test users...")

        headers = {
            "Authorization": f"Bearer {self.get_admin_token()}",
            "Content-Type": "application/json",
        }

        for user_data in TEST_USERS:
            username = user_data["username"]

            # Check if user exists
            response = requests.get(
                f"{self.base_url}/admin/realms/{REALM_NAME}/users",
                headers=headers,
                params={"username": username},
                timeout=10,
            )

            if response.status_code == 200 and response.json():
                logger.info(f"User {username} already exists")
                user_id = response.json()[0]["id"]
            else:
                # Create user
                user_config = {
                    "username": user_data["username"],
                    "email": user_data["email"],
                    "firstName": user_data["firstName"],
                    "lastName": user_data["lastName"],
                    "enabled": True,
                    "emailVerified": True,
                }

                response = requests.post(
                    f"{self.base_url}/admin/realms/{REALM_NAME}/users",
                    headers=headers,
                    json=user_config,
                    timeout=10,
                )

                if response.status_code != 201:
                    logger.error(f"Failed to create user {username}: {response.text}")
                    continue

                # Get user ID
                response = requests.get(
                    f"{self.base_url}/admin/realms/{REALM_NAME}/users",
                    headers=headers,
                    params={"username": username},
                    timeout=10,
                )
                user_id = response.json()[0]["id"]
                logger.info(f"User {username} created successfully")

            # Set password
            password_config = {
                "type": "password",
                "value": user_data["password"],
                "temporary": False,
            }

            response = requests.put(
                f"{self.base_url}/admin/realms/{REALM_NAME}/users/{user_id}/reset-password",
                headers=headers,
                json=password_config,
                timeout=10,
            )

            if response.status_code != 204:
                logger.error(f"Failed to set password for {username}: {response.text}")

            # Assign roles
            for role_name in user_data["roles"]:
                # Get role
                response = requests.get(
                    f"{self.base_url}/admin/realms/{REALM_NAME}/roles/{role_name}",
                    headers=headers,
                    timeout=10,
                )

                if response.status_code != 200:
                    logger.error(f"Role {role_name} not found")
                    continue

                role = response.json()

                # Assign role to user
                response = requests.post(
                    f"{self.base_url}/admin/realms/{REALM_NAME}/users/{user_id}/role-mappings/realm",
                    headers=headers,
                    json=[role],
                    timeout=10,
                )

                if response.status_code != 204:
                    logger.error(f"Failed to assign role {role_name} to {username}")
                else:
                    logger.info(f"Assigned role {role_name} to {username}")

    def run(self) -> None:
        """Run complete Keycloak setup."""
        try:
            self.wait_for_keycloak()
            self.create_realm()
            self.create_client()
            self.create_roles()
            self.create_test_users()

            logger.info("Keycloak setup completed successfully")
            logger.info(f"\nKeycloak Admin Console: {KEYCLOAK_URL}")
            logger.info(f"Admin Username: {ADMIN_USERNAME}")
            logger.info(f"Admin Password: {ADMIN_PASSWORD}")
            logger.info(f"\nRealm: {REALM_NAME}")
            logger.info(f"Client ID: {CLIENT_ID}")
            logger.info("\nTest Users:")
            for user in TEST_USERS:
                logger.info(f"  - {user['username']} / {user['password']} ({', '.join(user['roles'])})")

        except Exception as e:
            logger.error(f"Keycloak setup failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    setup = KeycloakSetup()
    setup.run()
