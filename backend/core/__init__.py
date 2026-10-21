from core.config import (
    DB_USER,
    DB_PASSWORD,
    DB_HOST,
    DB_PORT,
    DB_NAME,
    DATABASE_URL,
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    JWT_EXPIRACAO_MINUTOS,
    REDIS_URL,
    EMAIL_REGEX,
    PERMISSOES_VALIDAS,
    TTL_LIVRO,
    TTL_NAO_ENCONTRADO,
)
from core.database import engine, SessionLocal, Base, get_db
from core.security import (
    ErroCadastro,
    ErroAutenticacao,
    gerar_hash_senha,
    verificar_senha,
    gerar_token,
)
from core.redis_client import redis_client, get_redis
