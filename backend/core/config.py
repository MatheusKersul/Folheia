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

DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Configurações de Autenticação e Segurança (JWT e Bcrypt)
JWT_SECRET_KEY = (
    os.getenv("AUTH_SECRET")
    or os.getenv("JWT_SECRET_KEY", "troque-esta-chave-por-uma-segura-em-producao")
)
JWT_ALGORITHM = "HS256"
JWT_EXPIRACAO_MINUTOS = int(os.getenv("JWT_EXPIRACAO_MINUTOS", "60"))

# Configurações do Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Constantes de Domínio e Cache
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PERMISSOES_VALIDAS = {"usuario", "funcionario", "admin"}
BCRYPT_MAX_BYTES = 72

TTL_LIVRO = 3600            # 1 hora para livros encontrados
TTL_NAO_ENCONTRADO = 60     # 1 minuto para cache de livro não encontrado
