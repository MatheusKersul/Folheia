from typing import Optional
from sqlalchemy.orm import Session
from models.user import User

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Busca um usuário pelo endereço de e-mail utilizando SQLAlchemy ORM.
    """
    email_limpo = (email or "").strip().lower()
    return db.query(User).filter(User.email == email_limpo).first()

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """
    Busca um usuário pelo ID primário utilizando SQLAlchemy ORM.
    """
    return db.query(User).filter(User.id == user_id).first()

def create_user(
    db: Session,
    nome: str,
    email: str,
    senha_hash: str,
    permissoes: str = "usuario"
) -> User:
    """
    Persiste um novo usuário no banco de dados utilizando SQLAlchemy ORM.
    Executa commit e refresh garantindo integridade transacional.
    """
    novo_usuario = User(
        nome=nome.strip(),
        email=email.strip().lower(),
        senha=senha_hash,
        permissoes=permissoes or "usuario",
    )
    db.add(novo_usuario)
    try:
        db.commit()
        db.refresh(novo_usuario)
    except Exception:
        db.rollback()
        raise
    return novo_usuario

def list_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
    """
    Lista usuários cadastrados com paginação simples.
    """
    return db.query(User).offset(skip).limit(limit).all()

#ferramentas para o painel de adm