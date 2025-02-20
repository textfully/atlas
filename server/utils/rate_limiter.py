from api.types.enums import SubscriptionTier
from fastapi import HTTPException, Header, Security
from datetime import datetime, timedelta, timezone
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import time
from typing import Optional, Dict, Any, Tuple
from utils.redis_client import RedisClient
from utils.supabase_client import SupabaseClient
from api.auth import AuthService
from utils.logger import logger

security = HTTPBearer()


class RateLimiter:
    @staticmethod
    async def check_message_rate(
        user_id: str, tier: SubscriptionTier = SubscriptionTier.FREE
    ) -> Optional[Dict[str, str]]:
        """
        Check message rate limits:
        - All tiers: 1 message per second
        - Free tier: Also limited to 100 messages per day

        Args:
            user_id (str): The user's ID
            tier (SubscriptionTier): User's subscription tier

        Returns:
            Optional[Dict[str, str]]: Rate limit headers for free tier

        Raises:
            HTTPException: If rate limit is exceeded
        """
        redis = await RedisClient.get_client()
        current_time = time.time()

        # Check per-second rate limit (all tiers)
        second_key = f"rate:msg:second:{user_id}"
        last_message_time = await redis.get(second_key)

        if last_message_time:
            time_diff = current_time - float(last_message_time)
            if time_diff < 1:
                retry_after = 1 - time_diff
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Rate limit exceeded",
                        "message": "Please wait 1 second between messages",
                        "retry_after": round(retry_after, 2),
                        "type": "per_second_limit",
                    },
                )

        await redis.setex(second_key, 5, str(current_time))

        # For free tier, check daily message limit
        if tier == SubscriptionTier.FREE:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            daily_key = f"rate:msg:daily:{user_id}:{today}"

            # Get current count
            daily_count = await redis.get(daily_key)
            current_count = int(daily_count) if daily_count else 0

            if current_count >= 100:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Daily message limit exceeded",
                        "message": "Free tier is limited to 100 messages per day",
                        "retry_after": int(
                            (
                                datetime.combine(
                                    datetime.now(timezone.utc).date()
                                    + timedelta(days=1),
                                    datetime.min.time().replace(tzinfo=timezone.utc),
                                )
                                - datetime.now(timezone.utc)
                            ).total_seconds()
                        ),
                        "type": "daily_limit",
                        "upgrade_link": "https://textfully.dev/dashboard/billing/plan",
                    },
                )

            # Increment daily counter
            pipe = redis.pipeline()
            await pipe.incr(daily_key)
            await pipe.expire(daily_key, 36 * 3600)  # 36 hours expiry
            await pipe.execute()

            messages_remaining = 100 - (current_count + 1)
            return {
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Remaining": str(messages_remaining),
                "X-RateLimit-Reset-In-Seconds": str(
                    int(
                        (
                            datetime.combine(
                                datetime.now(timezone.utc).date() + timedelta(days=1),
                                datetime.min.time(),
                            ).replace(tzinfo=timezone.utc)
                            - datetime.now(timezone.utc)
                        ).total_seconds()
                    )
                ),
            }

        return None

    @staticmethod
    async def get_current_limits(
        user_id: str, tier: SubscriptionTier = SubscriptionTier.FREE
    ) -> Dict[str, Any]:
        """Get current rate limit status for a user

        Returns:
            Dict[str, Any]: Rate limit status
        """
        redis = await RedisClient.get_client()

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily_key = f"rate:msg:daily:{user_id}:{today}"
        daily_count = await redis.get(daily_key)
        current_count = int(daily_count) if daily_count else 0

        return {
            "tier": tier,
            "limits": {
                "per_second": 1,
                "per_day": 100 if tier == SubscriptionTier.FREE else None,
                "messages_sent_today": current_count,
                "messages_remaining_today": (
                    max(0, 100 - current_count)
                    if tier == SubscriptionTier.FREE
                    else None
                ),
                "reset_in_seconds": (
                    int(
                        (
                            datetime.combine(
                                datetime.now(timezone.utc).date() + timedelta(days=1),
                                datetime.min.time(),
                            ).replace(tzinfo=timezone.utc)
                            - datetime.now(timezone.utc)
                        ).total_seconds()
                    )
                    if tier == SubscriptionTier.FREE
                    else None
                ),
            },
        }


async def get_user_tier(user_id: str) -> SubscriptionTier:
    """Get user's subscription tier

    Returns:
        SubscriptionTier: User's subscription tier
    """
    data, error = await SupabaseClient.fetch_user_data(user_id)

    if error or not data:
        return SubscriptionTier.FREE

    return data.get("subscription_tier", SubscriptionTier.FREE)


async def check_rate_limit(
    credentials: HTTPAuthorizationCredentials = Security(security),
    x_organization_id: str = Header(..., alias="X-Organization-ID"),
) -> Tuple[str, str, Optional[Dict[str, str]]]:
    """Rate limiting dependency for message endpoints

    Uses same authentication logic as verify_api_key for API key validation.

    Returns:
        Tuple[str, str, Optional[Dict[str, str]]]: Contains:
            - user_id (str): The authenticated user ID
            - organization_id (str): The verified organization ID
            - rate_limit_headers (Optional[Dict[str, str]]): Rate limit headers if applicable

    Raises:
        HTTPException: If API key is invalid
    """
    try:
        user_id = await AuthService.validate_api_key(credentials.credentials)

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid API key")

        data, error = await SupabaseClient.verify_organization_access(
            x_organization_id, user_id
        )
        if error or not data:
            raise HTTPException(
                status_code=403, detail="User does not have access to organization"
            )

        organization_id = data["organization_id"]

        tier = await get_user_tier(user_id)
        rate_limit_headers = await RateLimiter.check_message_rate(user_id, tier)

        return user_id, organization_id, rate_limit_headers
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check rate limit: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid API key")
