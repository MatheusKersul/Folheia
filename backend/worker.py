import os
import signal
import time
import logging

from services.queue_service import QueueService
from services.scraper_client import ScraperClient
from core.database import SessionLocal
# import crud / models necessários para salvar


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Worker %(process)d] %(message)s"
)


RUNNING = True


def handle_shutdown(signum, frame):
    global RUNNING
    logging.info(
        "Sinal de encerramento recebido. Finalizando após tarefa atual..."
    )
    RUNNING = False


def processar_tarefa(
    queue_service: QueueService,
    scraper_client: ScraperClient,
    tarefa: dict,
    worker_id: str = "worker"
):
    isbn = tarefa.get("isbn")

    if not isbn:
        logging.warning("Tarefa recebida sem ISBN. Ignorando.")
        return

    logging.info(f"Processando ISBN: {isbn}")
    inicio_tempo = time.perf_counter()

    # 1. Tenta adquirir o Lock Distribuído
    with queue_service.lock_isbn(isbn, ttl=120) as locked:

        if not locked:
            logging.warning(
                f"ISBN {isbn} já está sendo processado por outro worker. "
                "Pulando..."
            )
            return

        queue_service.rem_chave_temp(isbn)

        try:
            # 2. Chama o scraper-amazon através do Service Discovery
            dados = scraper_client.executar_scraping(isbn)
            duracao = round(time.perf_counter() - inicio_tempo, 2)

            if not dados:
                logging.warning(
                    f"Nenhum dado retornado para o ISBN {isbn}."
                )
                queue_service.salvar_resultado(
                    isbn,
                    [],
                    ttl=600
                )
                queue_service.registrar_metrica_tarefa(
                    worker_id=worker_id,
                    isbn=isbn,
                    duracao_segundos=duracao,
                    sucesso=False,
                    num_ofertas=0
                )
                return

            # 3. Salva o resultado no Redis
            try:
                queue_service.salvar_resultado(
                    isbn,
                    dados,
                    ttl=86400
                )

                queue_service.registrar_metrica_tarefa(
                    worker_id=worker_id,
                    isbn=isbn,
                    duracao_segundos=duracao,
                    sucesso=True,
                    num_ofertas=len(dados)
                )

                logging.info(
                    f"ISBN {isbn} pesquisado e salvo no Redis com sucesso em {duracao}s! "
                    f"({len(dados)} ofertas)"
                )

            except Exception as e:
                logging.error(
                    f"Erro ao processar o ISBN {isbn}: {e}",
                    exc_info=True
                )

            logging.info(
                f"ISBN {isbn} busca feita com sucesso!"
            )

        except Exception as e:
            duracao = round(time.perf_counter() - inicio_tempo, 2)
            queue_service.registrar_metrica_tarefa(
                worker_id=worker_id,
                isbn=isbn,
                duracao_segundos=duracao,
                sucesso=False,
                num_ofertas=0
            )
            logging.error(
                f"Erro ao processar ISBN {isbn}: {e}",
                exc_info=True
            )


def main():
    # Registra interceptadores de término de processo
    # (Docker stop / Ctrl+C)
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    worker_id = os.getenv("HOSTNAME", "local-worker")

    logging.info(
        f"Worker {worker_id} pronto e aguardando tarefas na fila..."
    )

    queue_service = QueueService()
    scraper_client = ScraperClient()

    while RUNNING:
        try:
            # Emite batimento cardíaco para a telemetria do Admin saber que o worker está vivo
            queue_service.registrar_heartbeat(worker_id)

            # BRPOP bloqueante (espera 5s por novas mensagens sem gastar CPU)
            tarefa = queue_service.obter_proxima_tarefa(timeout=5)

            if tarefa:
                processar_tarefa(
                    queue_service,
                    scraper_client,
                    tarefa,
                    worker_id=worker_id
                )

        except Exception as e:
            logging.error(
                f"Erro inesperado no loop do worker: {e}",
                exc_info=True
            )

            time.sleep(2)

    logging.info(
        f"Worker {worker_id} encerrado com sucesso."
    )


if __name__ == "__main__":
    main()
