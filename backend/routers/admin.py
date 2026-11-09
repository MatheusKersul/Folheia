import time
import json
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status
from core.redis_client import redis_client
from services.queue_service import QueueService

router = APIRouter(prefix="/admin", tags=["Administração e Telemetria"])
queue_service = QueueService()


def categorizar_chave(chave: str) -> str:
    """Classifica a chave do Redis por funcionalidade do sistema."""
    if chave.startswith("resultado:scrape:"):
        return "Ofertas Raspadas"
    elif chave.startswith("lock:scrape:"):
        return "Lock de Coordenação"
    elif chave.startswith("queue:") or chave.startswith("fila:"):
        return "Fila de Tarefas"
    elif chave.startswith("livro:"):
        return "Cache de Livros (Catálogo)"
    elif chave.startswith("worker:heartbeat:"):
        return "Heartbeat do Worker"
    elif chave.startswith("metrics:"):
        return "Métricas do Sistema"
    elif chave.startswith("ryw:"):
        return "Consistência de Replicação (RYW)"
    return "Outros"


@router.get("/telemetria/redis")
def obter_telemetria_redis() -> Dict[str, Any]:
    """
    Retorna o diagnóstico completo e em tempo real do Redis para o painel de administração:
    - Informações de memória (usada, pico, limite configurado, percentual de uso).
    - Estado das filas e locks de coordenação.
    - Status de saúde dos workers e tempo de resposta de cada um.
    - Relação e inspeção de todas as chaves salvas no Redis.
    """
    try:
        redis_client.ping()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Não foi possível conectar ao Redis: {str(e)}"
        )

    # 1. Informações de Memória
    info_mem = redis_client.info("memory")
    usada_bytes = int(info_mem.get("used_memory", 0))
    max_bytes = int(info_mem.get("maxmemory", 0))
    pico_human = info_mem.get("used_memory_peak_human", "N/A")
    usada_human = info_mem.get("used_memory_human", "N/A")
    max_human = info_mem.get("maxmemory_human", "Sem limite")
    politica_despejo = info_mem.get("maxmemory_policy", "volatile-lru")

    porcentagem_uso = round((usada_bytes / max_bytes * 100), 1) if max_bytes > 0 else 0.0

    # 2. Informações do Servidor
    info_server = redis_client.info("server")
    info_clients = redis_client.info("clients")
    info_stats = redis_client.info("stats")

    uptime_segundos = int(info_server.get("uptime_in_seconds", 0))
    dias = uptime_segundos // 86400
    horas = (uptime_segundos % 86400) // 3600
    minutos = (uptime_segundos % 3600) // 60

    # 3. Informações da Fila de Scraping
    tamanho_fila = queue_service.tamanho_fila()
    itens_em_espera = list(redis_client.smembers("fila:itens"))

    # 4. Locks Ativos
    chaves_locks = redis_client.keys("lock:scrape:*")
    locks_ativos = []
    for k in chaves_locks:
        isbn = k.replace("lock:scrape:", "")
        ttl_restante = redis_client.ttl(k)
        locks_ativos.append({
            "chave": k,
            "isbn": isbn,
            "ttl_segundos": ttl_restante
        })

    # 5. Workers e Desempenho
    chaves_heartbeats = redis_client.keys("worker:heartbeat:*")
    workers_online = []
    for k in chaves_heartbeats:
        worker_id = k.replace("worker:heartbeat:", "")
        ttl_hb = redis_client.ttl(k)
        # Snapshot de métricas salvas para esse worker
        dados_snapshot = redis_client.hgetall(f"metrics:worker:{worker_id}")
        workers_online.append({
            "worker_id": worker_id,
            "status": "Online",
            "segundos_para_expirar_heartbeat": ttl_hb,
            "ultimo_isbn": dados_snapshot.get("ultimo_isbn", "-"),
            "ultima_duracao_s": dados_snapshot.get("ultima_duracao_s", "-"),
            "ultimo_status": dados_snapshot.get("ultimo_status", "aguardando")
        })

    # Histórico recente de tarefas
    tarefas_recentes = queue_service.obter_tarefas_recentes(limit=15)
    
    # Cálculo do tempo médio das tarefas recentes
    tempos_validos = [t["duracao_s"] for t in tarefas_recentes if "duracao_s" in t and t.get("duracao_s", 0) > 0]
    tempo_medio = round(sum(tempos_validos) / len(tempos_validos), 2) if tempos_validos else 0.0

    # 6. Inspeção de Chaves
    todas_chaves = redis_client.keys("*")
    lista_chaves = []
    categorias_count: Dict[str, int] = {}

    for chave in todas_chaves:
        tipo = redis_client.type(chave)
        ttl = redis_client.ttl(chave)
        categoria = categorizar_chave(chave)
        categorias_count[categoria] = categorias_count.get(categoria, 0) + 1

        # Gera uma prévia resumida
        preview = ""
        try:
            if tipo == "string":
                val = redis_client.get(chave)
                if val and (val.startswith("[") or val.startswith("{")):
                    preview = f"JSON ({len(val)} chars)"
                else:
                    preview = (val[:40] + "...") if val and len(val) > 40 else (val or "")
            elif tipo == "list":
                tamanho = redis_client.llen(chave)
                preview = f"Lista com {tamanho} item(ns)"
            elif tipo == "set":
                tamanho = redis_client.scard(chave)
                preview = f"Conjunto com {tamanho} item(ns)"
            elif tipo == "hash":
                tamanho = redis_client.hlen(chave)
                preview = f"Hash com {tamanho} campo(s)"
        except Exception:
            preview = "Indisponível"

        lista_chaves.append({
            "chave": chave,
            "tipo": tipo,
            "ttl": ttl if ttl >= 0 else ("Sem expiração" if ttl == -1 else "Expirada"),
            "categoria": categoria,
            "preview": preview
        })

    # Ordena chaves por categoria e nome
    lista_chaves.sort(key=lambda x: (x["categoria"], x["chave"]))

    return {
        "status": "online",
        "timestamp": int(time.time()),
        "servidor": {
            "versao": info_server.get("redis_version", "Desconhecida"),
            "uptime_formatado": f"{dias}d {horas}h {minutos}m",
            "clientes_conectados": int(info_clients.get("connected_clients", 1)),
            "total_comandos_executados": int(info_stats.get("total_commands_processed", 0)),
            "porta": info_server.get("tcp_port", 6379),
            "modo": info_server.get("redis_mode", "standalone")
        },
        "memoria": {
            "usada_human": usada_human,
            "pico_human": pico_human,
            "max_human": max_human,
            "usada_bytes": usada_bytes,
            "max_bytes": max_bytes,
            "porcentagem_uso": porcentagem_uso,
            "politica_despejo": politica_despejo,
            "fragmentacao_ratio": float(info_mem.get("mem_fragmentation_ratio", 1.0))
        },
        "fila": {
            "chave": queue_service.queue_key,
            "total_pendentes": tamanho_fila,
            "itens_em_espera": itens_em_espera,
            "total_itens_espera": len(itens_em_espera),
            "locks_ativos": locks_ativos
        },
        "workers": {
            "total_online": len(workers_online),
            "lista_online": workers_online,
            "tarefas_recentes": tarefas_recentes,
            "tempo_medio_segundos": tempo_medio
        },
        "chaves": {
            "total": len(todas_chaves),
            "por_categoria": categorias_count,
            "lista": lista_chaves
        }
    }


@router.post("/limpar-fila")
def limpar_fila_tarefas():
    """Remove todas as tarefas pendentes da fila do Redis."""
    total = redis_client.delete("queue:scrape", "fila:itens")
    return {"status": "sucesso", "mensagem": "Fila e itens em espera foram zerados.", "chaves_removidas": total}


@router.delete("/chaves/{chave:path}")
def excluir_chave(chave: str):
    """Permite ao administrador excluir manualmente uma chave de teste ou cache."""
    removido = bool(redis_client.delete(chave))
    if not removido:
        raise HTTPException(status_code=404, detail="Chave não encontrada no Redis.")
    return {"status": "sucesso", "mensagem": f"Chave '{chave}' excluída com sucesso."}
