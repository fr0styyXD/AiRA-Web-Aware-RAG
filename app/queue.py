import redis
import json
from app.config import REDIS_HOST, REDIS_PORT, REDIS_DB

class RedisQueue:
    """Simple Redis queue for managing URL processing jobs"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True
        )
        self.queue_name = "url_processing_queue"
    
    def enqueue(self, url: str):
        """Add a URL to the processing queue"""
        job_data = {
            "url": url
        }
        self.redis_client.rpush(self.queue_name, json.dumps(job_data))
    
    def dequeue(self) -> dict:
        """Get the next URL from the queue (blocking)"""
        # Block for 1 second waiting for a job
        result = self.redis_client.blpop(self.queue_name, timeout=1)
        if result:
            _, job_data = result
            return json.loads(job_data)
        return None
    
    def get_queue_length(self) -> int:
        """Get the current queue length"""
        return self.redis_client.llen(self.queue_name)
    
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        try:
            self.redis_client.ping()
            return True
        except:
            return False
