from dotenv import load_dotenv

from services.queue_service import QueueService
from services.scraper_client import ScraperClient
from worker import processar_tarefa


load_dotenv()


class QueueServiceTeste(QueueService):
    def __init__(self):
        pass

    def lock_isbn(self, isbn, ttl=120):
        class LockTeste:
            def __enter__(self):
                print(f"Lock adquirido para ISBN {isbn}")
                return True

            def __exit__(self, exc_type, exc_value, traceback):
                print(f"Lock liberado para ISBN {isbn}")

        return LockTeste()

    def rem_chave_temp(self, isbn):
        print(f"Chave temporária removida: {isbn}")

    def salvar_resultado(self, isbn, dados, ttl=86400):
        print(f"Resultado salvo para {isbn}: {len(dados)} ofertas")


scraper_client = ScraperClient()
queue_service = QueueServiceTeste()

tarefa = {
    "isbn": "9788594540188"
}

processar_tarefa(
    queue_service,
    scraper_client,
    tarefa
)