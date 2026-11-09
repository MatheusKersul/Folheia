import uuid
import json
import time
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from core.redis_client import redis_client

class QueueService:
    # COORDENAÇÃO FILA
    def __init__(self, client=redis_client):
        self.redis = client
        self.queue_key = "queue:scrape"

    def enfileirar_scrape(self, isbn: str, scp: str = "amazon", prioridade: bool = False) -> int:
        """
        Adiciona uma tarefa à fila do Redis.
        - prioridade=False: LPUSH (entra no fim da prioridade normal FIFO com BRPOP)
        - prioridade=True: RPUSH (entra mais perto da saída do BRPOP)
        """
        payload = json.dumps({"isbn": isbn, "scp": scp})
        if prioridade:
            return self.redis.rpush(self.queue_key, payload)
        else:
            return self.redis.lpush(self.queue_key, payload)

    def tamanho_fila(self) -> int:
        return self.redis.llen(self.queue_key)

    def add_chave_temp(self, isbn: str):
        self.redis.sadd("fila:itens", isbn)

    def check_chave_temp(self, isbn: str):
        return self.redis.sismember("fila:itens", isbn)

    def rem_chave_temp(self, isbn: str):
        if self.redis.sismember("fila:itens", isbn):
            self.redis.srem("fila:itens", isbn)

    def obter_proxima_tarefa(self, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """
        O worker pega a próxima tarefa. Se a fila estiver vazia, ele bloqueia até timeout.
        """
        resultado = self.redis.brpop(self.queue_key, timeout=timeout)
        if resultado:
            _, item_json = resultado  # brpop retorna tupla (chave, valor)
            return json.loads(item_json)
        return None

    # COORDENAÇÃO LOCK
    @contextmanager
    def coordination_locks(self, string_lock: str, ttl: int = 3600):
        """
        SET NX EX + DEL: Garante que apenas 1 worker processe este recurso simultaneamente.
        """
        lock_key = f"lock:scrape:{string_lock}"
        token = str(uuid.uuid4())

        # Adquire lock atômico
        adquirido = self.redis.set(lock_key, token, nx=True, ex=ttl)
        if not adquirido:
            yield False
            return

        try:
            yield True
        finally:
            # Libera o lock apenas se o token for o deste processo
            if self.redis.get(lock_key) == token:
                self.redis.delete(lock_key)

    # Alias para compatibilidade
    def lock_isbn(self, isbn: str, ttl: int = 120):
        return self.coordination_locks(string_lock=isbn, ttl=ttl)

    def lock_ativo(self, string_lock: str) -> bool:
        """Verifica se existe um lock em andamento para o recurso."""
        lock_key = f"lock:scrape:{string_lock}"
        return bool(self.redis.exists(lock_key))

    def _chave_resultado(self, isbn: str) -> str:
        return f"resultado:scrape:{isbn}"

    def salvar_resultado(self, isbn: str, dados: list[dict], ttl: int = 86400) -> bool:
        """
        [CREATE / UPDATE]
        Salva as ofertas no Redis em formato JSON.
        TTL padrão: 86400 segundos (24 horas de cache).
        """
        chave = self._chave_resultado(isbn)
        conteudo = json.dumps(dados, ensure_ascii=False)
        return bool(self.redis.set(chave, conteudo, ex=ttl))

    def obter_resultado(self, isbn: str) -> Optional[list[dict]]:
        """
        [READ]
        Recupera as ofertas do Redis e já converte de volta para lista de dicionários.
        Retorna None se ainda não existir ou tiver expirado.
        """
        chave = self._chave_resultado(isbn)
        dado_bruto = self.redis.get(chave)
        if dado_bruto:
            try:
                return json.loads(dado_bruto)
            except json.JSONDecodeError:
                return None
        return None

    def existe_resultado(self, isbn: str) -> bool:
        chave = self._chave_resultado(isbn)
        return bool(self.redis.exists(chave))

    def deletar_resultado(self, isbn: str) -> bool:
        """
        [DELETE]
        Remove o cache caso precise forçar uma nova raspagem limpa.
        """
        chave = self._chave_resultado(isbn)
        return bool(self.redis.delete(chave))


    def registrar_heartbeat(self, worker_id: str, ttl: int = 25):
        self.redis.set(f"worker:heartbeat:{worker_id}", str(time.time()), ex=ttl)

    def registrar_metrica_tarefa(
        self,
        worker_id: str,
        isbn: str,
        duracao_segundos: float,
        sucesso: bool = True,
        num_ofertas: int = 0
    ):
        """Registra a conclusão de uma tarefa de scraping para monitoramento."""
        registro = {
            "worker_id": worker_id,
            "isbn": isbn,
            "duracao_s": round(duracao_segundos, 2),
            "sucesso": sucesso,
            "ofertas": num_ofertas,
            "timestamp": int(time.time())
        }
        # Armazena na lista de histórico recente (mantém até 50 execuções)
        self.redis.lpush("metrics:worker:historico", json.dumps(registro))
        self.redis.ltrim("metrics:worker:historico", 0, 49)

        # Atualiza o snapshot do worker
        self.redis.hset(
            f"metrics:worker:{worker_id}",
            mapping={
                "ultimo_isbn": isbn,
                "ultima_duracao_s": str(round(duracao_segundos, 2)),
                "ultimo_timestamp": str(int(time.time())),
                "ultimo_status": "sucesso" if sucesso else "falha"
            }
        )

    def obter_tarefas_recentes(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Recupera as últimas tarefas processadas pelos workers."""
        itens = self.redis.lrange("metrics:worker:historico", 0, limit - 1)
        tarefas = []
        for raw in itens:
            try:
                tarefas.append(json.loads(raw))
            except Exception:
                pass
        return tarefas
