import logging
import redis
from redis.sentinel import Sentinel
from core.config import (
    REDIS_URL,
    REDIS_USE_SENTINEL,
    REDIS_SENTINEL_HOSTS,
    REDIS_SENTINEL_MASTER_NAME
)

logger = logging.getLogger(__name__)

sentinel_instance = None
redis_master = None
redis_replica = None
redis_client = None

if REDIS_USE_SENTINEL:
    try:
        # Conexão com Sentinels (timeout de consulta aos Sentinels: 2s)
        sentinel_instance = Sentinel(
            REDIS_SENTINEL_HOSTS,
            socket_timeout=2.0,
            decode_responses=True
        )
        # Aponta para o Master atual.
        # IMPORTANTE: socket_timeout não deve ser curto (ex: 1.0s) pois o worker utiliza
        # comandos bloqueantes como BRPOP(timeout=5s). Usamos socket_connect_timeout=3.0 e socket_timeout=None.
        redis_master = sentinel_instance.master_for(
            REDIS_SENTINEL_MASTER_NAME,
            socket_connect_timeout=3.0,
            socket_timeout=None
        )
        # Aponta para uma réplica aleatória para leituras distribuídas
        redis_replica = sentinel_instance.slave_for(
            REDIS_SENTINEL_MASTER_NAME,
            socket_connect_timeout=3.0,
            socket_timeout=None
        )
        redis_client = redis_master
        logger.info(f"[Redis Sentinel] Conectado ao cluster com Master '{REDIS_SENTINEL_MASTER_NAME}' via {REDIS_SENTINEL_HOSTS}")
    except Exception as e:
        logger.warning(f"[Redis Sentinel] Falha ao conectar via Sentinel ({e}). Usando fallback direto: {REDIS_URL}")
        redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
else:
    # Modo direto (standalone / desenvolvimento)
    redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def get_redis():
    """Retorna a instância do Redis Master para operações de escrita e coordenação."""
    return redis_client


def get_redis_replica():
    """Retorna uma réplica para leitura caso configurada, ou o próprio cliente padrão."""
    return redis_replica if redis_replica is not None else redis_client
