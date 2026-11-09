from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from core.config import DATABASE_URL, DATABASE_URL_REPLICA


engine = create_engine(DATABASE_URL, pool_pre_ping=True)

engine_replica = create_engine(
    DATABASE_URL_REPLICA or DATABASE_URL,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
SessionReplica = sessionmaker(autocommit=False, autoflush=False, bind=engine_replica)
Base = declarative_base()


# --- Dependências para rotas FastAPI ---

def get_db() -> Generator:
    """
    Dependência FastAPI para a instância Primária (Escrita / Modificação).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_read() -> Generator:
    """
    Dependência FastAPI para a Réplica de Leitura.
    Ideal para rotas 100% de leitura (como busca de catálogo).
    """
    db = SessionReplica()
    try:
        yield db
    finally:
        db.close()


# --- Context Managers para uso direto em scripts / workers / services ---

@contextmanager
def db_session() -> Generator:
    """
    Context manager para uso direto da sessão primária fora do FastAPI:
    
    Exemplo:
        with db_session() as db:
            usuario = db.query(User).first()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_read_session() -> Generator:
    """
    Context manager para uso direto da réplica fora do FastAPI:
    
    Exemplo:
        with db_read_session() as db:
            livros = db.query(Edition).all()
    """
    db = SessionReplica()
    try:
        yield db
    finally:
        db.close()
