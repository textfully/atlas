from api.types.enums import SubscriptionTier
from api.auth import verify_api_key
from fastapi import HTTPException, Security, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import time
from typing import Optional, Dict, Any, Tuple
from utils.redis_client import RedisClient
from utils.supabase_client import SupabaseClient
from utils.logger import logger

security = HTTPBearer()


async def get_organization_tier(organization_id: str) -> SubscriptionTier:
    """Get organization's subscription tier

    Args:
        organization_id (str): Organization ID

    Returns:
        SubscriptionTier: Organization's subscription tier
    """
    data, error = await SupabaseClient.fetch_organization(organization_id)

    if error or not data:
        logger.error(f"Failed to fetch organization tier: {error}")
        return SubscriptionTier.FREE

    return SubscriptionTier(data["subscription_tier"])


class RateLimiter:
    @staticmethod
    async def check_message_rate(organization_id: str) -> None:
        """Check per-second rate limit for messages (1 message per second)

        Args:
            organization_id (str): The organization's ID

        Raises:
            HTTPException: If rate limit is exceeded
        """
        redis = await RedisClient.get_client()
        current_time = time.time()
        daily_key = f"rate:msg:daily:{organization_id}"

        # Get count of messages in the current second
        count = await redis.zcount(
            daily_key,
            min=current_time - 1,  # Last second
            max=current_time,  # Current time
        )

        if count >= 1:
            # Get the timestamp of the first message that will expire from the current second
            messages_in_window = await redis.zrangebyscore(
                daily_key, min=current_time - 1, max=current_time, withscores=True
            )
            if messages_in_window:
                oldest_in_second = messages_in_window[0][1]
                retry_after = oldest_in_second + 1 - current_time
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Rate limit exceeded",
                        "message": "Maximum 1 message per second",
                        "retry_after": round(retry_after, 3),
                        "type": "per_second_limit",
                    },
                )

    @staticmethod
    async def increment_daily_count(organization_id: str) -> None:
        """Increment the daily message count for an organization

        Args:
            organization_id (str): The organization's ID
        """
        redis = await RedisClient.get_client()
        current_time = time.time()
        daily_key = f"rate:msg:daily:{organization_id}"

        # Add current timestamp to sorted set
        await redis.zadd(daily_key, {str(current_time): current_time})

        # Remove messages older than 24 hours
        cutoff_time = current_time - (24 * 60 * 60)
        await redis.zremrangebyscore(daily_key, "-inf", cutoff_time)

        # Set key expiration to 24 hours from now to prevent storage buildup
        await redis.expire(daily_key, 24 * 60 * 60)

    @staticmethod
    async def get_daily_count(organization_id: str) -> int:
        """Get the number of messages sent in the last 24 hours

        Args:
            organization_id (str): The organization's ID

        Returns:
            int: Number of messages sent in the last 24 hours
        """
        redis = await RedisClient.get_client()
        daily_key = f"rate:msg:daily:{organization_id}"
        cutoff_time = time.time() - (24 * 60 * 60)

        # Remove old entries and get count of remaining ones
        await redis.zremrangebyscore(daily_key, "-inf", cutoff_time)
        count = await redis.zcard(daily_key)
        return count

    @staticmethod
    async def get_current_limits(organization_id: str, tier: SubscriptionTier) -> Dict:
        """Get current rate limit status for an organization

        Args:
            organization_id (str): Organization ID
            tier (SubscriptionTier): Organization's subscription tier

        Returns:
            Dict: Rate limit status
        """
        daily_count = await RateLimiter.get_daily_count(organization_id)
        daily_limit = 100 if tier == SubscriptionTier.FREE else float("inf")

        return {
            "limits": {
                "per_second": 1,
                "per_day": daily_limit,
                "messages_sent_today": daily_count,
                "messages_remaining_today": (
                    max(0, daily_limit - daily_count)
                    if tier == SubscriptionTier.FREE
                    else None
                ),
            }
        }

    @staticmethod
    async def check_rate_limit(
        organization_id: str, tier: SubscriptionTier
    ) -> Dict[str, str]:
        """Check if organization has exceeded daily rate limits

        Args:
            organization_id (str): Organization ID
            tier (SubscriptionTier): Organization's subscription tier

        Returns:
            Dict[str, str]: Rate limit headers if limits exceeded

        Raises:
            HTTPException: If daily limit is exceeded
        """
        redis = await RedisClient.get_client()
        daily_key = f"rate:msg:daily:{organization_id}"
        current_time = time.time()
        cutoff_time = current_time - (24 * 60 * 60)

        # Remove old entries and get timestamps of remaining ones
        await redis.zremrangebyscore(daily_key, "-inf", cutoff_time)
        oldest_msg_time = await redis.zrange(daily_key, 0, 0, withscores=True)
        daily_count = await redis.zcard(daily_key)
        daily_limit = 100 if tier == SubscriptionTier.FREE else float("inf")

        # Check if daily limit exceeded
        if daily_count >= daily_limit and oldest_msg_time:
            # Get the timestamp of the oldest message in the window
            oldest_time = oldest_msg_time[0][1] if oldest_msg_time else current_time
            # The next available slot is 24 hours after the oldest message
            retry_after = int(oldest_time + (24 * 60 * 60) - current_time)

            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Daily message limit exceeded",
                    "message": "Free tier is limited to 100 messages per rolling 24-hour period",
                    "retry_after": retry_after,
                    "type": "daily_limit",
                    "upgrade_link": "https://textfully.dev/dashboard/billing/plan",
                },
            )

        return {
            "X-RateLimit-Limit": str(daily_limit),
            "X-RateLimit-Remaining": str(daily_limit - daily_count),
        }


async def check_rate_limit(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> Tuple[str, str, Dict[str, str]]:
    """Check rate limits for API requests

    Args:
        credentials (HTTPAuthorizationCredentials): The authorization credentials

    Returns:
        Tuple[str, str, Dict[str, str]]: Contains:
            - user_id (str): User ID
            - organization_id (str): Organization ID
            - rate_limit_headers (Dict[str, str]): Rate limit headers

    Raises:
        HTTPException: If rate limit exceeded
    """
    user_id, organization_id = await verify_api_key(credentials)

    # Check per-second rate limit (applies to all organizations)
    await RateLimiter.check_message_rate(organization_id)

    # Check daily rate limit
    tier = await get_organization_tier(organization_id)

    # Check if we've exceeded limits
    rate_limit_headers = await RateLimiter.check_rate_limit(organization_id, tier)

    return user_id, organization_id, rate_limit_headers
