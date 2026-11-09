import re
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
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


def _normalizar_isbn(isbn: Optional[str]) -> Optional[str]:
    if isbn is None:
        return None
    limpo = re.sub(r"[\s-]", "", isbn).upper()
    return limpo or None


def _validar_isbn(isbn: Optional[str]) -> Optional[str]:
    digitos = _normalizar_isbn(isbn)
    
    if digitos is not None and len(digitos) != 13:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"O ISBN '{isbn}' é inválido: deve conter exatamente 13 dígitos numéricos.",
        )
    return digitos


def _item_ou_404(db: Session, usuario: User, item_id: int) -> ItemBiblioteca:
    try:
        link = crud_library.get_item_for_user(db, item_id, usuario.id)
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro no banco de dados ao buscar o item {item_id}: {str(e)}",
        )

    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item com ID {item_id} não foi encontrado na biblioteca do usuário '{usuario.nome}'.",
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
    """
    skip = (page - 1) * limit
    try:
        itens, total = crud_library.list_items(
            db, usuario_id=usuario.id, skip=skip, limit=limit, termo=termo
        )
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao consultar itens da biblioteca pessoal: {str(e)}",
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
    """
    if payload.edition_id is not None:
        try:
            edition = crud_book.get_edition_visible_to(db, payload.edition_id, usuario.id)
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro no banco ao buscar edição com ID {payload.edition_id}: {str(e)}",
            )
        if edition is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Obra com edition_id={payload.edition_id} não foi encontrada no catálogo ou não está disponível.",
            )
    else:
        isbn = _validar_isbn(payload.isbn)
        try:
            edition = crud_book.get_verified_edition_by_isbn(db, isbn) if isbn else None
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro no banco ao buscar edição com ISBN {isbn}: {str(e)}",
            )
        if edition is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Nenhuma obra oficial foi encontrada no catálogo com o ISBN '{payload.isbn}'.",
            )

    try:
        biblioteca = crud_library.get_or_create_library(db, usuario.id)
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao carregar/criar a biblioteca do usuário: {str(e)}",
        )

    if crud_library.get_link(db, biblioteca.id, edition.id) is not None:
        identificador = f"edition_id={edition.id}" if payload.edition_id else f"ISBN='{payload.isbn}'"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A obra '{edition.titulo}' ({identificador}) já está adicionada na sua biblioteca.",
        )

    try:
        link = crud_library.add_link(db, biblioteca.id, edition.id)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Conflito de unicidade: a obra '{edition.titulo}' já consta na sua biblioteca.",
        )
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao vincular a obra à biblioteca: {str(e)}",
        )

    return _item_ou_404(db, usuario, link.id)


def criar_edicao_propria(
    db: Session, usuario: User, payload: CriarEdicaoPropriaRequest
) -> ItemBiblioteca:
    """
    Cria uma edição própria (não oficial) e já a vincula à biblioteca do usuário.
    """
    isbn = _validar_isbn(payload.isbn)

    if isbn is not None:
        try:
            edicao_oficial = crud_book.get_verified_edition_by_isbn(db, isbn)
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro no banco ao validar ISBN oficial: {str(e)}",
            )
        if edicao_oficial is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Já existe uma edição oficial cadastrada com o ISBN '{payload.isbn}' "
                    f"('{edicao_oficial.titulo}'). Adicione-a diretamente pelo catálogo em POST /biblioteca/livros."
                ),
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

    try:
        biblioteca = crud_library.get_or_create_library(db, usuario.id)
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao carregar/criar a biblioteca do usuário: {str(e)}",
        )

    try:
        link = crud_library.create_custom_edition_and_link(
            db, biblioteca.id, dados
        )
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Não foi possível criar a edição própria: conflito com dados existentes (ISBN duplicado ou restrição violada). Detalhes: {str(e.orig) if hasattr(e, 'orig') else str(e)}",
        )
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao salvar edição própria e vincular à biblioteca: {str(e)}",
        )

    return _item_ou_404(db, usuario, link.id)


def listar_edicoes_proprias(
    db: Session, usuario: User, page: int = 1, limit: int = 20
) -> RespostaEdicoesProprias:
    skip = (page - 1) * limit
    try:
        edicoes, total = crud_library.list_custom_editions(
            db, usuario_id=usuario.id, skip=skip, limit=limit
        )
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao consultar edições próprias: {str(e)}",
        )

    return RespostaEdicoesProprias(
        total=total,
        page=page,
        limit=limit,
        edicoes=[EdicaoBiblioteca.from_edition(edition) for edition in edicoes],
    )


def remover_item(db: Session, usuario: User, item_id: int) -> None:
    try:
        link = crud_library.get_item_for_user(db, item_id, usuario.id)
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro no banco ao verificar item para remoção: {str(e)}",
        )

    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item com ID {item_id} não foi encontrado na sua biblioteca (ou já foi removido).",
        )

    try:
        crud_library.delete_link(db, link)
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao remover o item {item_id} da biblioteca: {str(e)}",
        )
