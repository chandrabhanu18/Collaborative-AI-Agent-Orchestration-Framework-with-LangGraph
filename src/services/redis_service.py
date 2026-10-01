"""
Redis service providing ephemeral scratchpad storage and pub/sub messaging.
"""
import json
import logging
from typing import Any, Optional, AsyncGenerator
import redis
import redis.asyncio as aioredis
from src.config.settings import settings

logger = logging.getLogger(__name__)


class RedisService:
    def __init__(self, url: Optional[str] = None):
        self.url = url or settings.REDIS_URL
        self._sync_client: Optional[redis.Redis] = None
        self._async_client: Optional[aioredis.Redis] = None

    @property
    def sync_client(self) -> redis.Redis:
        if self._sync_client is None:
            self._sync_client = redis.from_url(self.url, decode_responses=True)
        return self._sync_client

    @property
    def async_client(self) -> aioredis.Redis:
        if self._async_client is None:
            self._async_client = aioredis.from_url(self.url, decode_responses=True)
        return self._async_client

    @staticmethod
    def get_scratchpad_key(task_id: str) -> str:
        """Key pattern: task:<task_id>:workspace"""
        return f"task:{task_id}:workspace"

    @staticmethod
    def get_channel_name(task_id: str) -> str:
        """Channel pattern: channel:task:<task_id>"""
        return f"channel:task:{task_id}"

    # Synchronous Scratchpad methods (for Celery workers & sync agent steps)
    def set_scratchpad(self, task_id: str, data: Any, expire_seconds: int = 86400) -> bool:
        """Writes data to task:<task_id>:workspace scratchpad key."""
        key = self.get_scratchpad_key(task_id)
        if isinstance(data, (dict, list)):
            serialized = json.dumps(data)
        else:
            serialized = str(data)
        try:
            self.sync_client.set(key, serialized, ex=expire_seconds)
            return True
        except Exception as e:
            logger.error(f"Error setting Redis scratchpad for task {task_id}: {e}")
            return False

    def get_scratchpad(self, task_id: str) -> Optional[Any]:
        """Reads data from task:<task_id>:workspace scratchpad key."""
        key = self.get_scratchpad_key(task_id)
        try:
            val = self.sync_client.get(key)
            if val is None:
                return None
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return val
        except Exception as e:
            logger.error(f"Error reading Redis scratchpad for task {task_id}: {e}")
            return None

    def delete_scratchpad(self, task_id: str) -> bool:
        """Deletes task:<task_id>:workspace scratchpad key."""
        key = self.get_scratchpad_key(task_id)
        try:
            self.sync_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error deleting Redis scratchpad for task {task_id}: {e}")
            return False

    # Synchronous Pub/Sub (for Celery worker to broadcast status transitions)
    def publish_status(self, task_id: str, status: str):
        """Publishes task status update to task channel."""
        channel = self.get_channel_name(task_id)
        payload = json.dumps({"task_id": str(task_id), "status": str(status)})
        try:
            self.sync_client.publish(channel, payload)
        except Exception as e:
            logger.error(f"Error publishing status {status} for task {task_id}: {e}")

    # Asynchronous Scratchpad methods (for async API if needed)
    async def async_set_scratchpad(self, task_id: str, data: Any, expire_seconds: int = 86400) -> bool:
        key = self.get_scratchpad_key(task_id)
        if isinstance(data, (dict, list)):
            serialized = json.dumps(data)
        else:
            serialized = str(data)
        try:
            await self.async_client.set(key, serialized, ex=expire_seconds)
            return True
        except Exception as e:
            logger.error(f"Async error setting Redis scratchpad for task {task_id}: {e}")
            return False

    async def async_get_scratchpad(self, task_id: str) -> Optional[Any]:
        key = self.get_scratchpad_key(task_id)
        try:
            val = await self.async_client.get(key)
            if val is None:
                return None
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return val
        except Exception as e:
            logger.error(f"Async error reading Redis scratchpad for task {task_id}: {e}")
            return None

    # Asynchronous Pub/Sub subscription (for FastAPI WebSockets)
    async def subscribe_task_updates(self, task_id: str) -> AsyncGenerator[dict, None]:
        """Subscribes to Redis channel and yields status update dictionaries."""
        channel_name = self.get_channel_name(task_id)
        pubsub = self.async_client.pubsub()
        try:
            await pubsub.subscribe(channel_name)
            async for message in pubsub.listen():
                if message["type"] == "message":
                    raw_data = message["data"]
                    try:
                        parsed = json.loads(raw_data)
                        yield parsed
                    except Exception:
                        yield {"task_id": task_id, "status": raw_data}
        except Exception as e:
            logger.error(f"Pub/sub subscription error for task {task_id}: {e}")
        finally:
            try:
                await pubsub.unsubscribe(channel_name)
                await pubsub.close()
            except Exception:
                pass


redis_service = RedisService()
