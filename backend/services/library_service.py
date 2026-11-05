import re
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from crud import crud_book, crud_library
from models.user import User
from schemas.library import (
    AdicionarLivroRequest,
    CriarEdicaoPropriaRequest,
    EdicaoBiblioteca,
    ItemBiblioteca,
    RespostaBiblioteca,
    RespostaEdicoesProprias,
)

ITEM_NAO_ENCONTRADO = "Item não encontrado na sua biblioteca."
EDICAO_NAO_ENCONTRADA = "Obra não encontrada no catálogo."
ITEM_DUPLICADO = "Esta obra já está na sua biblioteca."
ISBN_DUPLICADO = (
    "Já existe uma edição oficial com este ISBN. "
    "Adicione-a pelo catálogo em POST /biblioteca/livros."
)


def _normalizar_isbn(isbn: Optional[str]) -> Optional[str]:
    if isbn is None:
        return None
    digitos = re.sub(r"\D", "", isbn)
    return digitos or None


def _validar_isbn(isbn: Optional[str]) -> Optional[str]:
    digitos = _normalizar_isbn(isbn)
    if digitos is not None and len(digitos) != 13:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O ISBN deve conter exatamente 13 dígitos.",
        )
    return digitos


def _item_ou_404(db: Session, usuario: User, item_id: int) -> ItemBiblioteca:
    link = crud_library.get_item_for_user(db, item_id, usuario.id)
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ITEM_NAO_ENCONTRADO,
        )
    return ItemBiblioteca.from_link(link)


def listar_biblioteca(
    db: Session,
    usuario: User,
    page: int = 1,
    limit: int = 20,
    termo: Optional[str] = None,
) -> RespostaBiblioteca:
    """
    Lista a biblioteca pessoal do usuário autenticado.

    O escopo é sempre ``Library.id_usuario == usuario.id``: não existe
    parâmetro de cliente capaz de apontar para a biblioteca de outra pessoa.
    """
    skip = (page - 1) * limit
    itens, total = crud_library.list_items(
        db, usuario_id=usuario.id, skip=skip, limit=limit, termo=termo
    )

    return RespostaBiblioteca(
        total=total,
        page=page,
        limit=limit,
        itens=[ItemBiblioteca.from_link(link) for link in itens],
    )


def obter_item(db: Session, usuario: User, item_id: int) -> ItemBiblioteca:
    return _item_ou_404(db, usuario, item_id)


def adicionar_livro(
    db: Session, usuario: User, payload: AdicionarLivroRequest
) -> ItemBiblioteca:
    """
    Adiciona à biblioteca uma obra do catálogo oficial.

    Edições privadas de terceiros são indistinguíveis de inexistentes (404).
    """
    if payload.edition_id is not None:
        edition = crud_book.get_edition_visible_to(db, payload.edition_id, usuario.id)
    else:
        isbn = _validar_isbn(payload.isbn)
        edition = crud_book.get_verified_edition_by_isbn(db, isbn) if isbn else None

    if edition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=EDICAO_NAO_ENCONTRADA,
        )

    biblioteca = crud_library.get_or_create_library(db, usuario.id)

    if crud_library.get_link(db, biblioteca.id, edition.id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ITEM_DUPLICADO,
        )

    try:
        link = crud_library.add_link(db, biblioteca.id, edition.id)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ITEM_DUPLICADO,
        )

    return _item_ou_404(db, usuario, link.id)


def criar_edicao_propria(
    db: Session, usuario: User, payload: CriarEdicaoPropriaRequest
) -> ItemBiblioteca:
    """
    Cria uma edição própria (não oficial) e já a vincula à biblioteca do usuário.

    Regras:
    - ``verificada=False`` e ``id_usuario_criador`` = usuário autenticado;
    - ISBN opcional; se informado e já existir no catálogo oficial, orienta
      o uso do catálogo (evita duplicidade de obra oficial);
    - visível apenas para o criador.
    """
    isbn = _validar_isbn(payload.isbn)

    if isbn is not None and crud_book.get_verified_edition_by_isbn(db, isbn) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ISBN_DUPLICADO,
        )

    dados = {
        "isbn_13": isbn,
        "titulo": payload.titulo,
        "autor": payload.autor,
        "data_publicacao": payload.data_publicacao,
        "formato": payload.formato,
        "num_paginas": payload.num_paginas,
        "editora": payload.editora,
        "id_usuario_criador": usuario.id,
    }

    biblioteca = crud_library.get_or_create_library(db, usuario.id)

    try:
        link = crud_library.create_custom_edition_and_link(
            db, biblioteca.id, dados
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ISBN_DUPLICADO,
        )

    return _item_ou_404(db, usuario, link.id)


def listar_edicoes_proprias(
    db: Session, usuario: User, page: int = 1, limit: int = 20
) -> RespostaEdicoesProprias:
    skip = (page - 1) * limit
    edicoes, total = crud_library.list_custom_editions(
        db, usuario_id=usuario.id, skip=skip, limit=limit
    )

    return RespostaEdicoesProprias(
        total=total,
        page=page,
        limit=limit,
        edicoes=[EdicaoBiblioteca.from_edition(edition) for edition in edicoes],
    )


def remover_item(db: Session, usuario: User, item_id: int) -> None:
    link = crud_library.get_item_for_user(db, item_id, usuario.id)
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ITEM_NAO_ENCONTRADO,
        )
    crud_library.delete_link(db, link)
