import re
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field

from services.queue_service import QueueService
from schemas.scrap import ScrapeStatusResponse

router = APIRouter(prefix="/scp", tags=["Scrapper"])
queue_service = QueueService()

class ScrapeRequest(BaseModel):
    isbn: str = Field(..., description="ISBN-10 ou ISBN-13 do livro", example="9788594540188")
    scp: str = Field("amazon", description="Identificador do scraper a utilizar (ex: amazon, mercadolivre)")
    prioridade: bool = Field(False, description="Se deve furar a fila normal")

class ScrapeResponse(BaseModel):
    status: str
    mensagem: str
    isbn: str
    scp: str
    tarefas_na_fila: Optional[int] = None

def normalizar_isbn(isbn: str) -> str:
    limpo = re.sub(r"[\s-]", "", isbn).upper()
    if len(limpo) not in (10, 13):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ISBN inválido: '{isbn}'. Deve conter 10 ou 13 dígitos."
        )
    return limpo

@router.post("/enfileirar", response_model=ScrapeResponse, status_code=status.HTTP_202_ACCEPTED)
async def enfileirar_scraping(requisicao: ScrapeRequest):
    """
    Recebe um ISBN e enfileira para os workers processarem em segundo plano.
    - Se o ISBN já estiver sob processamento (lock ativo), avisa sem duplicar trabalho.
    - Retorna HTTP 202 imediatamente sem prender a conexão.
    """
    isbn_limpo = normalizar_isbn(requisicao.isbn)
    ja_na_fila = queue_service.check_chave_temp(isbn_limpo)
    em_processamento = queue_service.lock_ativo(isbn_limpo)

    # 1. Verifica se já existe um worker com lock ativo processando esse ISBN

    if ja_na_fila or em_processamento:
        return ScrapeResponse(
            status="em_andamento",
            mensagem=f"O ISBN {isbn_limpo} já está sendo processado por um scraper.",
            isbn=isbn_limpo,
            scp=requisicao.scp,
            tarefas_na_fila=queue_service.tamanho_fila()
        )
    
    queue_service.add_chave_temp(isbn_limpo)

    # 2. Enfileira a tarefa via LPUSH / RPUSH conforme prioridade
    posicao = queue_service.enfileirar_scrape(
        isbn=isbn_limpo,
        scp=requisicao.scp,
        prioridade=requisicao.prioridade
    )
    return ScrapeResponse(
        status="enfileirado",
        mensagem="Tarefa enviada para a fila de scraping com sucesso.",
        isbn=isbn_limpo,
        scp=requisicao.scp,
        tarefas_na_fila=posicao
    )

@router.get("/status/{isbn}",
            response_model = ScrapeStatusResponse,
            summary="Consulta o status e resultado do scraping",
            description="Verifica se o scrapping do isbn está em andamento ou retorna as ofertas capturadas"
            )
async def status_scraping(isbn: str):
    """
    Verifica se um ISBN específico está atualmente sendo processado por algum worker.
    """
    isbn_limpo = normalizar_isbn(isbn)
    em_processamento = queue_service.lock_ativo(isbn_limpo)
    resultado_redis = queue_service.obter_resultado(isbn_limpo)

    if em_processamento:
        status_atual = "em_processamento"
    elif resultado_redis is not None:
        status_atual = "concluido"
    elif queue_service.check_chave_temp(isbn_limpo):
        status_atual = "aguardando na fila"
    else:
        status_atual = "não encontrado"

    ofertas_salvas = resultado_redis or []

    return ScrapeStatusResponse(
        isbn=isbn_limpo,
        status=status_atual,
        em_processamento=em_processamento,
        ofertas=ofertas_salvas
    )

@router.get("/fila/tamanho")
async def tamanho_fila():
    """
    Retorna a quantidade de tarefas pendentes na fila do Redis.
    """
    return {
        "fila": queue_service.queue_key,
        "total_pendentes": queue_service.tamanho_fila()
    }