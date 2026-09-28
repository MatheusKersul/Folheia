import os
import sys
import typesense

# Configurações de conexão
TYPESENSE_HOST = os.getenv("TYPESENSE_HOST", "localhost")
TYPESENSE_PORT = os.getenv("TYPESENSE_PORT", "8108")
TYPESENSE_PROTOCOL = os.getenv("TYPESENSE_PROTOCOL", "http")
TYPESENSE_API_KEY = os.getenv("TYPESENSE_API_KEY", "Hu52dwsas2AdxdE")

def get_client() -> typesense.Client:
    """Retorna o cliente Typesense configurado."""
    return typesense.Client({
        "nodes": [{
            "host": TYPESENSE_HOST,
            "port": TYPESENSE_PORT,
            "protocol": TYPESENSE_PROTOCOL
        }],
        "api_key": TYPESENSE_API_KEY,
        "connection_timeout_seconds": 5
    })

def buscar_documentos(client: typesense.Client, collection_name: str, query: str = "*", query_by: str = None, filter_by: str = None, sort_by: str = None, per_page: int = 10):
    """Executa a busca na collection informada."""
    # Se query_by não for informado, busca por todos os campos do tipo string indexados
    if not query_by:
        try:
            col_info = client.collections[collection_name].retrieve()
            string_fields = [f["name"] for f in col_info.get("fields", []) if "string" in f.get("type", "")]
            query_by = ",".join(string_fields) if string_fields else "titulo"
        except Exception:
            query_by = "titulo,autor"

    search_params = {
        "q": query,
        "query_by": query_by,
        "per_page": per_page
    }

    if filter_by:
        search_params["filter_by"] = filter_by
    if sort_by:
        search_params["sort_by"] = sort_by

    return client.collections[collection_name].documents.search(search_params)

def exibir_resultados(resultado: dict):
    """Exibe os resultados da pesquisa de forma organizada."""
    total = resultado.get("found", 0)
    hits = resultado.get("hits", [])
    tempo_ms = resultado.get("search_time_ms", 0)

    print(f"\n> Encontrados: {total} registro(s) em {tempo_ms} ms")
    if not hits:
        print("  Nenhum resultado para os critérios informados.")
        return

    for idx, hit in enumerate(hits, start=1):
        doc = hit.get("document", {})
        print(f"\n [{idx}] ID: {doc.get('id', 'N/A')}")
        for chave, valor in doc.items():
            if chave != "id":
                print(f"     - {chave}: {valor}")

def main():
    print("=" * 65)
    print(" BUSCA TYPESENSE - APENAS CONSULTA")
    print(f" Conectando a {TYPESENSE_PROTOCOL}://{TYPESENSE_HOST}:{TYPESENSE_PORT}")
    print("=" * 65)

    client = get_client()

    # 1. Obter collections existentes
    try:
        collections = client.collections.retrieve()
    except Exception as e:
        print(f"[ERRO] Não foi possível conectar ao Typesense: {e}")
        return

    if not collections:
        print("[AVISO] Nenhuma collection encontrada no Typesense.")
        return

    print("\nCollections disponíveis:")
    for i, col in enumerate(collections, start=1):
        print(f" {i}. {col['name']} ({col.get('num_documents', 0)} documentos)")

    # Define a collection padrão (usa 'livros_teste' se existir, ou a primeira)
    nomes_cols = [c["name"] for c in collections]
    collection_name = "livros_teste" if "livros_teste" in nomes_cols else nomes_cols[0]
    print(f"\n-> Usando collection: '{collection_name}'")

    # 2. Se um termo foi passado via linha de comando, busca por ele
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(f"\nRealizando busca por: '{query}'")
        res = buscar_documentos(client, collection_name, query=query)
        exibir_resultados(res)
        return

    # 3. Demonstração de buscas padrão nos dados existentes
    print("\n" + "-" * 65)
    print(" 1. Listando os primeiros documentos existentes (busca aberta '*')")
    print("-" * 65)
    res_todos = buscar_documentos(client, collection_name, query="*")
    exibir_resultados(res_todos)

    print("\n" + "-" * 65)
    print(" 2. Teste de busca por termo com tolerância a erro ('Machdo')")
    print("-" * 65)
    res_termo = buscar_documentos(client, collection_name, query="Machdo")
    exibir_resultados(res_termo)

    # 4. Modo interativo de busca no terminal
    print("\n" + "=" * 65)
    print(" MODO INTERATIVO (Digite o que deseja buscar ou 'sair' para encerrar)")
    print("=" * 65)

    while True:
        try:
            termo = input("\nDigite o termo de busca (ou * para todos): ").strip()
            if not termo or termo.lower() in ["sair", "exit", "quit"]:
                print("Encerrando.")
                break
            
            res = buscar_documentos(client, collection_name, query=termo)
            exibir_resultados(res)
        except (KeyboardInterrupt, EOFError):
            print("\nEncerrando.")
            break

if __name__ == "__main__":
    main()
