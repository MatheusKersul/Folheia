from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.database import get_db
from database.replica_fallback import db_safe_session, marcar_escrita_recente
from core.deps import get_current_user
from models.user import User
from schemas.library import (
    AdicionarLivroRequest,
    CriarEdicaoPropriaRequest,
    ItemBiblioteca,
    RespostaBiblioteca,
    RespostaEdicoesProprias,
)
from services.library_service import (
    adicionar_livro,
    criar_edicao_propria,
    listar_biblioteca,
    listar_edicoes_proprias,
    obter_item,
    remover_item,
)

router = APIRouter(prefix="/biblioteca", tags=["Biblioteca pessoal"])


@router.get("", response_model=RespostaBiblioteca)
def rota_listar_biblioteca(
    page: int = Query(1, ge=1, description="Página (1-based)"),
    limit: int = Query(20, ge=1, le=100, description="Itens por página"),
    q: Optional[str] = Query(
        None, max_length=200, description="Busca por título, autor ou editora"
    ),
    usuario: User = Depends(get_current_user),
):
    """
    Lista a biblioteca pessoal do usuário autenticado.
    Usa db_safe_session: lê da réplica, exceto se o usuário escreveu recentemente.
    """
    with db_safe_session(usuario.id) as db:
        return listar_biblioteca(db=db, usuario=usuario, page=page, limit=limit, termo=q)


@router.post(
    "/livros",
    response_model=ItemBiblioteca,
    status_code=status.HTTP_201_CREATED,
)
def rota_adicionar_livro(
    payload: AdicionarLivroRequest,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Adiciona à biblioteca uma obra do catálogo oficial (Escrita na Primária).
    """
    item = adicionar_livro(db=db, usuario=usuario, payload=payload)
    marcar_escrita_recente(usuario.id)
    return item


@router.post(
    "/edicoes-proprias",
    response_model=ItemBiblioteca,
    status_code=status.HTTP_201_CREATED,
)
def rota_criar_edicao_propria(
    payload: CriarEdicaoPropriaRequest,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Cria uma edição própria (não oficial) e a adiciona à biblioteca (Escrita na Primária).
    """
    item = criar_edicao_propria(db=db, usuario=usuario, payload=payload)
    marcar_escrita_recente(usuario.id)
    return item


@router.get("/edicoes-proprias", response_model=RespostaEdicoesProprias)
def rota_listar_edicoes_proprias(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    usuario: User = Depends(get_current_user),
):
    """
    Lista as edições próprias do usuário autenticado.
    Usa db_safe_session: lê da réplica ou da primária se houver escrita recente.
    """
    with db_safe_session(usuario.id) as db:
        return listar_edicoes_proprias(db=db, usuario=usuario, page=page, limit=limit)


@router.get("/itens/{item_id}", response_model=ItemBiblioteca)
def rota_obter_item(
    item_id: int,
    usuario: User = Depends(get_current_user),
):
    """
    Detalha um item da biblioteca pessoal do usuário autenticado.
    """
    with db_safe_session(usuario.id) as db:
        return obter_item(db=db, usuario=usuario, item_id=item_id)


@router.delete("/itens/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def rota_remover_item(
    item_id: int,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove um item da biblioteca pessoal (Escrita na Primária).
    """
    remover_item(db=db, usuario=usuario, item_id=item_id)
    marcar_escrita_recente(usuario.id)
