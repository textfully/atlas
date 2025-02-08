from api.types.enums import ApiKeyPermission
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timezone
import secrets
import hashlib
from typing import Optional, Tuple
from utils.supabase_client import SupabaseClient
from utils.logger import logger

security = HTTPBearer()


class AuthService:
    @staticmethod
    def generate_api_key() -> str:
        """Generate a new API key with tx_ prefix

        Returns:
            str: New API key
        """
        return f"tx_{secrets.token_hex(32)}"

    @staticmethod
    def get_short_key(api_key: str) -> str:
        """Get shortened version of the API key

        Returns:
            str: Shortened API key
        """
        if not api_key.startswith("tx_"):
            raise ValueError("Invalid API key format")
        return api_key[:11]  # Return "tx_" + first 8 chars

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash the API key using SHA-256

        Returns:
            str: Hashed API key
        """
        return hashlib.sha256(api_key.encode()).hexdigest()

    @classmethod
    async def create_api_key(
        cls,
        user_id: str,
        name: str,
        permission: ApiKeyPermission = ApiKeyPermission.ALL,
    ) -> Tuple[str, str]:
        """Create a new API key for a user

        Args:
            user_id (str): User ID
            name (str): API key name
            permission (ApiKeyPermission): API key permission

        Returns:
            Tuple[str, str]: New API key and its shortened version

        Raises:
            HTTPException: If API key creation fails
        """
        api_key = cls.generate_api_key()
        hashed_key = cls.hash_api_key(api_key)
        short_key = cls.get_short_key(api_key)
        created_at = datetime.now(timezone.utc).isoformat()

        api_key_data = {
            "user_id": user_id,
            "key_hash": hashed_key,
            "short_key": short_key,
            "created_at": created_at,
            "last_used": created_at,
            "is_active": True,
            "name": name,
            "permission": permission,
        }

        _, error = await SupabaseClient.store_api_key(api_key_data)
        if error:
            logger.error(f"Failed to create API key: {error}")
            raise HTTPException(status_code=500, detail="Failed to create API key")

        return api_key, created_at

    @classmethod
    async def validate_api_key(cls, api_key: str) -> Optional[str]:
        """Validate an API key and return user_id if valid

        Args:
            api_key (str): API key

        Returns:
            Optional[str]: User ID if API key is valid

        Raises:
            HTTPException: If API key validation fails
        """
        # Check for tx_ prefix
        if not api_key.startswith("tx_"):
            return None

        hashed_key = cls.hash_api_key(api_key)
        data, error = await SupabaseClient.validate_api_key(hashed_key)

        if error or not data:
            return None

        # Check if API key is active
        if not data["is_active"]:
            raise HTTPException(
                status_code=401,
                detail="API key has been revoked. Please generate a new API key.",
            )

        # Update last used timestamp
        _, error = await SupabaseClient.update_api_key_last_used(
            data["user_id"], hashed_key, datetime.now(timezone.utc).isoformat()
        )

        if error:
            logger.error(f"Failed to update API key: {error}")
            raise HTTPException(status_code=500, detail="Failed to update API key")

        return data["user_id"]


async def verify_bearer_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    """Verify bearer token and return user_id

    Returns:
        str: User ID

    Raises:
        HTTPException: If bearer token is invalid
    """
    token = credentials.credentials

    if token.startswith("tx_"):
        return await verify_api_key(credentials)
    else:
        return await verify_auth_token(credentials)


async def verify_auth_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    """Verify authentication token and return user_id

    Returns:
        str: User ID

    Raises:
        HTTPException: If authentication token is invalid
    """
    try:
        user_id = await SupabaseClient.verify_token(credentials.credentials)

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid authentication token")

        return user_id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authentication token")


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    """Verify API key and return user_id

    Returns:
        str: User ID

    Raises:
        HTTPException: If API key is invalid
    """
    try:
        user_id = await AuthService.validate_api_key(credentials.credentials)

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid API key")

        return user_id
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to verify API key: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid API key")
