from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from schemas.book import RespostaLivros, RespostaBusca
from services.book_service import buscar_livro_com_cache, buscar_precos_ofertas

router = APIRouter(tags=["Livros e Preços"])

@router.get("/buscar-livros", response_model=RespostaLivros)
async def rota_buscar_livros(
    tipo: Optional[str] = None,
    termo: str = "",
    db: Session = Depends(get_db)
):
    """
    Busca as informações cadastrais de uma obra no catálogo.
    Aceita busca por:
    - 'titulo': Busca textual no título
    - 'autor': Busca textual no nome do autor
    - 'isbn': Busca exata pelo ISBN-13
    Utiliza cache inteligente no Redis.
    """
    return await buscar_livro_com_cache(db=db, tipo=tipo, termo=termo)


@router.get("/buscar-precos/{termo_busca}", response_model=RespostaBusca)
async def rota_buscar_precos(
    termo_busca: str,
    isbn: str = "Não informado"
):
    """
    Retorna as ofertas e preços encontrados para determinado título/ISBN.
    """
    return await buscar_precos_ofertas(termo_busca=termo_busca, isbn=isbn)
