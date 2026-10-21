import asyncio
import logging
from typing import Optional
from fastapi import HTTPException, status
import redis
from sqlalchemy.orm import Session
from core.config import TTL_LIVRO, TTL_NAO_ENCONTRADO
from core.redis_client import redis_client
from crud.crud_book import find_book
from schemas.book import RespostaLivros, OfertaLivro, RespostaBusca

logger = logging.getLogger("folheia.cache")

async def buscar_livro_com_cache(
    db: Session,
    tipo: Optional[str],
    termo: str,
    cache_client: Optional[redis.Redis] = None,
) -> RespostaLivros:
    """
    Busca um livro com estratégia de cache-aside no Redis:
    1. Verifica cache no Redis.
    2. Se não encontrado no cache, consulta via SQLAlchemy ORM.
    3. Se encontrado no banco, armazena no Redis com TTL de 1 hora.
    4. Se inexistente no banco, armazena marcador negativo ('null') por 60 segundos
       para evitar sobrecarga (cache penetration / dog-piling).
    """
    r_client = cache_client or redis_client

    termo_limpo = (termo or "").strip()
    if not termo_limpo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campo de busca vazio"
        )

    tipo_limpo = (tipo or "").strip().lower()
    if tipo_limpo not in {"isbn", "titulo", "autor"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de busca inválido: '{tipo}'. Tipos válidos: 'isbn', 'titulo', 'autor'."
        )

    # Monta a chave de cache normalizada
    if tipo_limpo == "isbn":
        termo_formatado = termo_limpo.replace("-", "").strip()
    else:
        termo_formatado = " ".join(termo_limpo.lower().split())
    chave_consulta = f"livro:{tipo_limpo}:{termo_formatado}"

    # 1. Consulta ao cache Redis (com fail-safe se o Redis estiver indisponível)
    cached_value = None
    try:
        cached_value = r_client.get(chave_consulta)
    except Exception as err:
        print(f"[REDIS AVISO] Falha ao ler cache ({chave_consulta}): {err}")
        cached_value = None

    if cached_value == "null":
        print(f"[REDIS HIT NEGATIVO] Chave '{chave_consulta}' em cache como inexistente.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhuma obra encontrada para '{termo_limpo}'"
        )
    if cached_value:
        try:
            print(f"[REDIS HIT] Obra recuperada do Redis: {chave_consulta}")
            return RespostaLivros.model_validate_json(cached_value)
        except Exception:
            pass  # Se JSON do cache estiver corrompido, reconsulta banco

    print(f"[REDIS MISS] Chave '{chave_consulta}' nao encontrada no cache. Consultando banco de dados...")

    # 2. Consulta ao banco de dados via ORM
    try:
        livro = find_book(db, tipo=tipo_limpo, termo=termo_limpo)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err)
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno ao consultar o banco de dados: {str(err)}"
        )

    # 3. Trata livro não encontrado
    if not livro:
        try:
            r_client.set(chave_consulta, "null", ex=TTL_NAO_ENCONTRADO)
            print(f"[REDIS SET NEGATIVO] Chave '{chave_consulta}' salva como 'null' (TTL {TTL_NAO_ENCONTRADO}s).")
        except Exception as err:
            print(f"[REDIS AVISO] Falha ao salvar marcador negativo: {err}")

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhuma obra encontrada para '{termo_limpo}'"
        )

    resposta = RespostaLivros.from_edition(livro)

    # 4. Salva no cache com TTL padrão (1 hora)
    try:
        r_client.set(chave_consulta, resposta.model_dump_json(), ex=TTL_LIVRO)
        print(f"[REDIS SET] Obra salva no cache com sucesso: '{chave_consulta}' (TTL {TTL_LIVRO}s).")
    except Exception as err:
        print(f"[REDIS AVISO] Falha ao salvar no cache: {err}")

    return resposta


async def buscar_precos_ofertas(
    termo_busca: str,
    isbn: str = "Não informado"
) -> RespostaBusca:
    """
    Retorna ofertas agregadas de preços de lojas/marketplaces.
    Atualmente simula com mock para integração do frontend.
    """
    await asyncio.sleep(5)

    ofertas_encontradas = [
        OfertaLivro(loja="Mercado livre", preco=45.90, link="linkmercadolivre"),
        OfertaLivro(loja="Shopee", preco=35.90, link="linkshopee"),
        OfertaLivro(
            loja="Amazon",
            preco=55.90,
            link="https://www.amazon.com.br/FRANKENSTEIN-OUTRAS-HIST%C3%93RIAS-HORROR-JUNJI-ebook/dp/B09HW2WTPR/?_encoding=UTF8&pd_rd_w=onFf5&content-id=amzn1.sym.761077be-03f4-471e-82eb-e510d48b59aa&pf_rd_p=761077be-03f4-471e-82eb-e510d48b59aa&pf_rd_r=WK9S1AT5SMMGW55AZSBS&pd_rd_wg=X6CGY&pd_rd_r=53299eca-1dc5-4de8-aa92-7270946f9c75&ref_=pd_hp_d_r_atf_mtech-exp-p13ndeals"
        ),
    ]

    return RespostaBusca(titulo=termo_busca, isbn=isbn, ofertas=ofertas_encontradas)
