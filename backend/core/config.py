import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Carrega o .env localizado na pasta backend ou no diretório atual
backend_dir = Path(__file__).resolve().parent.parent
env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# Configurações do Banco de Dados PostgreSQL (RDS)
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "")
DB_REPLICA_HOST = os.getenv("DB_REPLICA_HOST", "").strip()

# URL de conexão da instância primária (escrita)
DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# URL de conexão da réplica de leitura
DATABASE_URL_REPLICA = (
    os.getenv("DATABASE_URL_REPLICA")
    or (
        f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_REPLICA_HOST}:{DB_PORT}/{DB_NAME}"
        if DB_REPLICA_HOST
        else None
    )
)

# Configurações de Autenticação e Segurança (JWT e Bcrypt)
JWT_SECRET_KEY = (
    os.getenv("AUTH_SECRET")
    or os.getenv("JWT_SECRET_KEY", "troque-esta-chave-por-uma-segura-em-producao")
)
JWT_ALGORITHM = "HS256"
JWT_EXPIRACAO_MINUTOS = int(os.getenv("JWT_EXPIRACAO_MINUTOS", "60"))

# Configurações do Redis e Sentinel
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_USE_SENTINEL = os.getenv("REDIS_USE_SENTINEL", "false").lower() in ("true", "1", "yes")
REDIS_SENTINEL_HOSTS_RAW = os.getenv("REDIS_SENTINEL_HOSTS", "sentinel-1:26379,sentinel-2:26379,sentinel-3:26379")
REDIS_SENTINEL_MASTER_NAME = os.getenv("REDIS_SENTINEL_MASTER_NAME", "mymaster")

def parse_sentinel_hosts(hosts_raw: str):
    hosts = []
    for item in hosts_raw.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" in item:
            host, port = item.split(":")
            hosts.append((host, int(port)))
        else:
            hosts.append((item, 26379))
    return hosts

REDIS_SENTINEL_HOSTS = parse_sentinel_hosts(REDIS_SENTINEL_HOSTS_RAW)

# Constantes de Domínio e Cache
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PERMISSOES_VALIDAS = {"usuario", "funcionario", "admin"}
BCRYPT_MAX_BYTES = 72

TTL_LIVRO = 3600            # 1 hora para livros encontrados
TTL_NAO_ENCONTRADO = 60     # 1 minuto para cache de livro não encontrado
