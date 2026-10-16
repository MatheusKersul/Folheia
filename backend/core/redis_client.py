import redis
from core.config import REDIS_URL

# Instância compartilhada do cliente Redis
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def get_redis():
    
    return redis_client
