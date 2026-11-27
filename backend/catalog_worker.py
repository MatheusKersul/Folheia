import os
import signal
import time
import logging
from typing import Optional, Dict, Any, List

from core.database import SessionLocal
from services.queue_service import QueueService
from services.s3_service import upload_capa_por_url
from crud.crud_book import salvar_ou_atualizar_edicao_scraped

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [CatalogWorker %(process)d] %(message)s"
)

RUNNING = True


def handle_shutdown(signum, frame):
    global RUNNING
    logging.info("Sinal de encerramento recebido no CatalogWorker. Finalizando com segurança...")
    RUNNING = False


def selecionar_melhor_metadado(dados: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Dentre as ofertas raspadas, seleciona o item com maior riqueza de metadados
    (priorizando registros com título, autor, capa e ISBN).
    """
    if not dados:
        return None

    def pontuacao(item: Dict[str, Any]) -> int:
        pts = 0
        if item.get("titulo"):
            pts += 3
        if item.get("autor"):
            pts += 2
        if item.get("images_url"):
            pts += 3
        if item.get("editora"):
            pts += 1
        if item.get("isbn_13"):
            pts += 2
        if item.get("num_paginas"):
            pts += 1
        return pts

    return max(dados, key=pontuacao)


def processar_ingestao(queue_service: QueueService, tarefa: Dict[str, Any]):
    isbn = tarefa.get("isbn")
    dados = tarefa.get("dados") or []

    if not isbn and not dados:
        logging.warning("Tarefa de catálogo recebida sem dados ou ISBN. Ignorando.")
        return

    item_base = selecionar_melhor_metadado(dados)
    if not item_base:
        logging.warning("Nenhum dado válido encontrado para ingestão do ISBN %s.", isbn)
        return

    # Garante que o ISBN da tarefa esteja no dicionário se não estiver no item
    if not item_base.get("isbn_13") and isbn:
        item_base["isbn_13"] = isbn

    inicio = time.perf_counter()
    image_url_externa = item_base.get("images_url")
    s3_image_url: Optional[str] = None

    # 1. Se houver imagem externa, baixa para a memória e envia ao S3
    if image_url_externa and ("amazonaws.com" not in image_url_externa):
        try:
            logging.info("Enviando capa para o S3 para o ISBN %s...", isbn)
            s3_image_url = upload_capa_por_url(image_url=image_url_externa, isbn=isbn)
            if s3_image_url:
                logging.info("Capa salva no S3 com sucesso: %s", s3_image_url)
        except Exception as e:
            logging.error("Falha no upload da capa para o S3 (ISBN %s): %s", isbn, e, exc_info=True)
    elif image_url_externa and ("amazonaws.com" in image_url_externa):
        s3_image_url = image_url_externa

    # 2. Persiste ou atualiza a edição no PostgreSQL (RDS)
    db = SessionLocal()
    try:
        edicao = salvar_ou_atualizar_edicao_scraped(
            db=db,
            dados=item_base,
            s3_images_url=s3_image_url
        )
        duracao = round(time.perf_counter() - inicio, 2)
        logging.info(
            "Edição persistida no RDS com sucesso em %ss! ID=%s, ISBN=%s, Título='%s'",
            duracao,
            edicao.id,
            edicao.isbn_13,
            edicao.titulo,
        )
    except Exception as e:
        db.rollback()
        logging.error("Erro ao salvar edição no RDS para o ISBN %s: %s", isbn, e, exc_info=True)
    finally:
        db.close()


def main():
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    logging.info("CatalogWorker iniciado! Aguardando tarefas na fila 'queue:catalog:ingest'...")
    queue_service = QueueService()

    while RUNNING:
        try:
            tarefa = queue_service.obter_proxima_ingestao_catalogo(timeout=5)
            if tarefa:
                processar_ingestao(queue_service, tarefa)
        except Exception as e:
            logging.error("Erro inesperado no loop do CatalogWorker: %s", e, exc_info=True)
            time.sleep(2)

    logging.info("CatalogWorker finalizado com sucesso.")


if __name__ == "__main__":
    main()
