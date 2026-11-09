import os
import signal
import logging
from services.queue_service import QueueService
from scrappers.scraper_amazon import executar_scraping_amazon
from core.database import SessionLocal
# import crud / models necessários para salvar

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Worker %(process)d] %(message)s"
)

RUNNING = True

def handle_shutdown(signum, frame):
    global RUNNING
    logging.info("Sinal de encerramento recebido. Finalizando após tarefa atual...")
    RUNNING = False

def processar_tarefa(queue_service: QueueService, tarefa: dict):
    isbn = tarefa.get("isbn")
    if not isbn:
        logging.warning("Tarefa recebida sem ISBN. Ignorando.")
        return

    logging.info(f"Processando ISBN: {isbn}")

    # 1. Tenta adquirir o Lock Distribuído
    with queue_service.lock_isbn(isbn, ttl=120) as locked:
        if not locked:
            logging.warning(f"ISBN {isbn} já está sendo processado por outro worker. Pulando...")
            return
        queue_service.rem_chave_temp(isbn)
        try:
            # 2. Chama o scraper (BrightData / Amazon)
            dados = executar_scraping_amazon(isbn)

            if not dados:
                logging.warning(f"Nenhum dado retornado para o ISBN {isbn}.")
                queue_service.salvar_resultado(isbn, [], ttl=600) 
                return

            # 3. Salva no banco de dados (PostgreSQL)
            try:

                queue_service.salvar_resultado(isbn, dados, ttl = 86400)
                logging.info(f"ISBN {isbn} pesquisado e salvo no Redis com sucesso! ({len(dados)} ofertas)")

            except Exception as e:
                logging.error(f"Erro ao processo o isbn {isbn}: {e}", exc_info=True)        


            logging.info(f"ISBN {isbn} busca feita com sucesso!")

        except Exception as e:
            logging.error(f"Erro ao processar ISBN {isbn}: {e}", exc_info=True)


def main():
    # Registra interceptadores de término de processo (Docker stop / Ctrl+C)
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    worker_id = os.getenv("HOSTNAME", "local-worker")
    logging.info(f"Worker {worker_id} pronto e aguardando tarefas na fila...")

    queue_service = QueueService()

    while RUNNING:
        try:
            # BRPOP bloqueante (espera 5s por novas mensagens sem gastar CPU)
            tarefa = queue_service.obter_proxima_tarefa(timeout=5)

            if tarefa:
                processar_tarefa(queue_service, tarefa)

        except Exception as e:
            logging.error(f"Erro inesperado no loop do worker: {e}", exc_info=True)
            import time
            time.sleep(2)

    logging.info(f"Worker {worker_id} encerrado com sucesso.")

if __name__ == "__main__":
    main()