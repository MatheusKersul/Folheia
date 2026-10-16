from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from core.config import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    JWT_EXPIRACAO_MINUTOS,
    BCRYPT_MAX_BYTES,
)

# ------------------------- Exceções de domínio -------------------------
class ErroCadastro(Exception):
    """Falha de validação ou regra de negócio no cadastro."""
    pass

class ErroAutenticacao(Exception):
    """Credenciais inválidas no login."""
    pass


# ------------------------ Utilitários de senha -------------------------
def gerar_hash_senha(senha_plana: str) -> str:
    """Gera o hash bcrypt (com salt aleatório) de uma senha em texto plano."""
    if len(senha_plana.encode("utf-8")) > BCRYPT_MAX_BYTES:
        raise ErroCadastro("A senha é muito longa (máximo de 72 bytes).")

    salt = bcrypt.gensalt()
    return bcrypt.hashpw(senha_plana.encode("utf-8"), salt).decode("utf-8")

def verificar_senha(senha_plana: str, senha_hash: str) -> bool:
    """Compara a senha em texto plano com o hash salvo no banco."""
    try:
        return bcrypt.checkpw(
            senha_plana.encode("utf-8"), senha_hash.encode("utf-8")
        )
    except (ValueError, TypeError):
        # Hash corrompido ou formato inesperado nunca deve autenticar
        return False

def gerar_token(usuario: dict) -> str:
    """Gera um token JWT para a sessão do usuário autenticado."""
    agora = datetime.now(timezone.utc)
    user_id = usuario.get("id")
    email = usuario.get("Email") or usuario.get("email")
    permissoes = usuario.get("Permissoes") or usuario.get("permissoes")

    payload = {
        "sub": str(user_id),
        "email": email,
        "permissoes": permissoes,
        "iat": agora,
        "exp": agora + timedelta(minutes=JWT_EXPIRACAO_MINUTOS),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
