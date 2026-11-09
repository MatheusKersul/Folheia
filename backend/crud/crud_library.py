from typing import Optional, Tuple

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from models.book import Edition
from models.user import Library, LinkLibrary

NOME_BIBLIOTECA_PADRAO = "Minha Biblioteca"


# --------------------------- Biblioteca pessoal ---------------------------
def get_library_by_user(db: Session, usuario_id: int) -> Optional[Library]:
    """Retorna a biblioteca pessoal do usuário, se existir."""
    return db.query(Library).filter(Library.id_usuario == usuario_id).first()


def _criar_library(db: Session, usuario_id: int, nome: str) -> Library:
    biblioteca = Library(id_usuario=usuario_id, nome=nome)
    db.add(biblioteca)
    db.commit()
    db.refresh(biblioteca)
    return biblioteca


def get_or_create_library(
    db: Session, usuario_id: int, nome: str = NOME_BIBLIOTECA_PADRAO
) -> Library:
    """
    Garante a existência da biblioteca pessoal do usuário (idempotente).

    O ``UNIQUE (id_usuario)`` protege contra duas requisições concorrentes
    criarem bibliotecas duplicadas: a perdedora apenas relê a existente.
    """
    biblioteca = get_library_by_user(db, usuario_id)
    if biblioteca is not None:
        return biblioteca

    try:
        return _criar_library(db, usuario_id, nome)
    except IntegrityError:
        db.rollback()
        biblioteca = get_library_by_user(db, usuario_id)
        if biblioteca is None:
            raise
        return biblioteca


# ----------------------------- Itens da estante -----------------------------
def _query_items(db: Session, usuario_id: int):
    """
    Consulta base dos itens da biblioteca.

    O vínculo é sempre filtrado por ``Library.id_usuario`` — a única fonte de
    escopo é o usuário autenticado.
    """
    return (
        db.query(LinkLibrary)
        .join(Library, LinkLibrary.id_biblioteca == Library.id)
        .join(Edition, LinkLibrary.id_livro == Edition.id)
        .filter(Library.id_usuario == usuario_id)
    )


def list_items(
    db: Session,
    usuario_id: int,
    skip: int = 0,
    limit: int = 20,
    termo: Optional[str] = None,
) -> Tuple[list[LinkLibrary], int]:
    """Lista os itens da biblioteca do usuário com paginação e busca opcional."""
    query = _query_items(db, usuario_id)

    if termo and termo.strip():
        padrao = f"%{termo.strip()}%"
        query = query.filter(
            or_(
                Edition.titulo.ilike(padrao),
                Edition.autor.ilike(padrao),
                Edition.editora.ilike(padrao),
            )
        )

    total = query.count()

    itens = (
        query.options(
            joinedload(LinkLibrary.livro),
            joinedload(LinkLibrary.biblioteca),
        )
        .order_by(LinkLibrary.criado_em.desc(), LinkLibrary.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return itens, total


def get_item_for_user(
    db: Session, item_id: int, usuario_id: int
) -> Optional[LinkLibrary]:
    """
    Retorna um item somente se ele pertencer à biblioteca do usuário.

    Item de outro usuário retorna ``None`` (o chamador responde 404).
    """
    return (
        _query_items(db, usuario_id)
        .options(
            joinedload(LinkLibrary.livro),
            joinedload(LinkLibrary.biblioteca),
        )
        .filter(LinkLibrary.id == item_id)
        .first()
    )


def get_link(db: Session, biblioteca_id: int, edition_id: int) -> Optional[LinkLibrary]:
    """Verifica se a edição já está vinculada à biblioteca informada."""
    return (
        db.query(LinkLibrary)
        .filter(
            LinkLibrary.id_biblioteca == biblioteca_id,
            LinkLibrary.id_livro == edition_id,
        )
        .first()
    )


def add_link(db: Session, biblioteca_id: int, edition_id: int) -> LinkLibrary:
    """Vincula uma edição existente à biblioteca do usuário."""
    link = LinkLibrary(id_biblioteca=biblioteca_id, id_livro=edition_id)
    db.add(link)
    try:
        db.commit()
        db.refresh(link)
    except Exception:
        db.rollback()
        raise
    return link


def delete_link(db: Session, link: LinkLibrary) -> None:
    """Remove um item da biblioteca."""
    db.delete(link)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


# --------------------------- Edições próprias ---------------------------
def create_custom_edition_and_link(
    db: Session, biblioteca_id: int, dados: dict
) -> LinkLibrary:
    """
    Cria a edição própria (``verificada=False``) e o vínculo com a biblioteca
    na mesma transação — ou ambos são persistidos, ou nenhum.
    """
    edition = Edition(verificada=False, **dados)
    link = LinkLibrary(id_biblioteca=biblioteca_id)
    link.livro = edition

    db.add(link)
    try:
        db.commit()
        db.refresh(link)
    except Exception:
        db.rollback()
        raise
    return link


def list_custom_editions(
    db: Session, usuario_id: int, skip: int = 0, limit: int = 20
) -> Tuple[list[Edition], int]:
    """Lista as edições próprias (não verificadas) de um usuário."""
    query = db.query(Edition).filter(
        Edition.id_usuario_criador == usuario_id,
        Edition.verificada.is_(False),
    )
    total = query.count()
    edicoes = (
        query.order_by(Edition.id.desc()).offset(skip).limit(limit).all()
    )
    return edicoes, total
