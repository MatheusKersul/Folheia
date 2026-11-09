from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy.orm import Session
from core.database import SessionLocal, SessionReplica, get_db, get_db_read
from core.redis_client import redis_client

# Tempo padrão de lag de replicação (5 segundos de consistência Read-Your-Writes)
TTL_REPLICA_PADRAO = 5


def marcar_escrita_recente(usuario_id: int, ttl: int = TTL_REPLICA_PADRAO) -> None:
    """
    Sinaliza no Redis que o usuário realizou uma mutação recente (escrita/edição/deleção).
    Durante a janela de TTL, qualquer leitura desse usuário será roteada para a
    instância Primária, evitando que ele leia dados defasados por replication lag.
    """
    if usuario_id:
        chave = f"ryw:user:{usuario_id}"
        redis_client.set(chave, "1", ex=ttl)


def tem_escrita_recente(usuario_id: int) -> bool:
    """
    Retorna True se o usuário realizou uma escrita recente dentro da janela de lag.
    """
    if not usuario_id:
        return False
    chave = f"ryw:user:{usuario_id}"
    return bool(redis_client.exists(chave))


def get_session_factory(usuario_id: Optional[int] = None):
    """
    Decide dinamicamente qual pool de conexões usar:
    - Se o usuário escreveu recentemente: SessionLocal (Primária)
    - Caso contrário: SessionReplica (Réplica de leitura)
    """
    if usuario_id and tem_escrita_recente(usuario_id):
        return SessionLocal
    return SessionReplica


def get_replica_safe(usuario_id: Optional[int] = None) -> Generator[Session, None, None]:
    """
    Dependência / gerador seguro para leitura:
    Direciona para a Réplica, exceto se o usuário escreveu recentemente.
    """
    SessionFactory = get_session_factory(usuario_id)
    db = SessionFactory()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_safe_session(usuario_id: Optional[int] = None) -> Generator[Session, None, None]:
    """
    Context manager para leitura direta com 'with' em qualquer arquivo fora do FastAPI:
    
    Exemplo de uso:
        with db_safe_session(usuario_id=10) as db:
            itens = db.query(Item).all()
    """
    SessionFactory = get_session_factory(usuario_id)
    db = SessionFactory()
    try:
        yield db
    finally:
        db.close()
