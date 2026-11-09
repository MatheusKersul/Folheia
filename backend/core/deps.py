"""
Dependências reutilizáveis do FastAPI.

Concentra a autenticação via Bearer Token (JWT) usada pelas rotas que
precisam identificar o usuário autenticado. O identificador do usuário
vem SEMPRE do token assinado, nunca de parâmetros enviados pelo cliente.
"""
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import ErroToken, decodificar_token
from crud.crud_user import get_user_by_id
from models.user import User

# auto_error=False para respondermos com uma mensagem genérica e uniforme.
esquema_bearer = HTTPBearer(
    auto_error=False,
    description="Token JWT devolvido por POST /auth/login",
)

MENSAGEM_CREDENCIAIS_INVALIDAS = "Credenciais inválidas ou ausentes."


def _credenciais_invalidas() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=MENSAGEM_CREDENCIAIS_INVALIDAS,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credenciais: Optional[HTTPAuthorizationCredentials] = Depends(esquema_bearer),
    db: Session = Depends(get_db),
) -> User:
    """
    Resolve o usuário autenticado a partir do header ``Authorization: Bearer <jwt>``.

    Garantia de privacidade: todas as rotas protegidas derivam o escopo de dados
    exclusivamente do ``id`` presente no token assinado.
    """
    if credenciais is None or not credenciais.credentials:
        raise _credenciais_invalidas()

    if credenciais.scheme.lower() != "bearer":
        raise _credenciais_invalidas()

    try:
        payload = decodificar_token(credenciais.credentials)
    except ErroToken:
        raise _credenciais_invalidas()

    try:
        usuario_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise _credenciais_invalidas()

    usuario = get_user_by_id(db, usuario_id)
    if usuario is None:
        raise _credenciais_invalidas()

    return usuario


def get_current_user_optional(
    credenciais: Optional[HTTPAuthorizationCredentials] = Depends(esquema_bearer),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Versão opcional da dependência de autenticação.

    Retorna ``None`` quando não há token, sem interromper a requisição.
    Útil para rotas públicas que podem enriquecer a resposta quando o
    usuário está autenticado.
    """
    if credenciais is None or not credenciais.credentials:
        return None

    try:
        payload = decodificar_token(credenciais.credentials)
        return get_user_by_id(db, int(payload["sub"]))
    except (ErroToken, KeyError, TypeError, ValueError):
        return None
