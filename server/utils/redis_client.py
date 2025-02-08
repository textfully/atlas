from redis.asyncio import Redis
from typing import Optional, List
from config.settings import REDIS_HOST, REDIS_PORT, REDIS_SSL, REDIS_PASSWORD
from utils.logger import logger


class RedisClient:
    _instance: Optional[Redis] = None

    @classmethod
    async def get_client(cls) -> Redis:
        """Get Redis client instance"""
        if cls._instance is None:
            try:
                # Create Redis connection
                cls._instance = Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    password=REDIS_PASSWORD,
                    decode_responses=True,
                    ssl=REDIS_SSL,
                )
                logger.info("Connected to Redis")

            except Exception as e:
                logger.error(f"Failed to initialize Redis client: {str(e)}")
                raise

        return cls._instance

    @classmethod
    async def close(cls) -> None:
        """Close Redis connection"""
        if cls._instance is not None:
            await cls._instance.close()
            cls._instance = None

    @classmethod
    async def health_check(cls) -> bool:
        """Check Redis connection health"""
        try:
            client = await cls.get_client()
            return await client.ping()
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return False

    @classmethod
    async def clear_user_data(cls, user_id: str) -> None:
        """Clear all rate limiting data for a user

        Args:
            user_id: The ID of the user whose data should be cleared

        Raises:
            Exception: If the deletion operation fails
        """
        try:
            client = await cls.get_client()
            pattern = f"*:{user_id}:*"
            keys: List[str] = await client.keys(pattern)
            if keys:
                await client.delete(*keys)
        except Exception as e:
            logger.error(f"Failed to clear user data: {str(e)}")
            raise
