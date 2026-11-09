import os
import requests
import json
import time
import re
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BRIGHTDATA_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

DATASET_ID = "gd_lwhideng15g8jg63s7"


# =========================================================
# CONVERTER ISBN-13 PARA ISBN-10
# =========================================================

def isbn13_para_isbn10(isbn):
    """
    Converte ISBN-13 para ISBN-10 quando o ISBN-13 começa com 978.
    Retorna None se a entrada for inválida ou não puder ser convertida.
    """
    isbn = re.sub(r"[\s-]", "", isbn).upper()

    if not re.fullmatch(r"\d{13}", isbn):
        return None

    # ISBN-10 só pode ser derivado diretamente de ISBN-13 com prefixo 978.
    if not isbn.startswith("978"):
        return None

    nove_digitos = isbn[3:12]

    # Valida o dígito verificador do ISBN-13.
    soma13 = sum(
        int(digito) * (1 if indice % 2 == 0 else 3)
        for indice, digito in enumerate(isbn)
    )
    if soma13 % 10 != 0:
        return None

    # Calcula o dígito verificador ISBN-10.
    soma10 = sum(int(digito) * peso for digito, peso in zip(nove_digitos, range(10, 1, -1)))
    digito = (11 - (soma10 % 11)) % 11
    verificador = "X" if digito == 10 else str(digito)

    return nove_digitos + verificador


# =========================================================
# BUSCA POR URL
# =========================================================

def buscar_por_url(url_produto):

    endpoint = "https://api.brightdata.com/datasets/v3/scrape"

    params = {
        "dataset_id": DATASET_ID,
        "format": "json"
    }

    dados = {
        "input": [
            {
                "url": url_produto
            }
        ]
    }

    inicio = time.perf_counter()

    try:
        resposta = requests.post(
            endpoint,
            params=params,
            headers=HEADERS,
            json=dados,
            timeout=120
        )
        return resposta

    finally:
        duracao = time.perf_counter() - inicio
        print(f"\n[TEMPO] Consulta Bright Data por URL: {duracao:.2f} segundos")


# =========================================================
# BUSCA POR ISBN -> ISBN-10 -> ASIN POTENCIAL -> URL
# =========================================================

def buscar_por_isbn(isbn):

    inicio_total = time.perf_counter()

    isbn_limpo = re.sub(r"[\s-]", "", isbn).upper()

    if not re.fullmatch(r"\d{13}", isbn_limpo):
        print("ISBN inválido. Digite um ISBN-13 com 13 dígitos.")
        print(f"[TEMPO] Fluxo total: {time.perf_counter() - inicio_total:.2f} segundos")
        return None

    inicio_conversao = time.perf_counter()
    isbn10 = isbn13_para_isbn10(isbn_limpo)
    tempo_conversao = time.perf_counter() - inicio_conversao

    print(f"\nISBN-13 informado: {isbn_limpo}")

    if isbn10 is None:
        print(
            "Não foi possível converter este ISBN-13 para ISBN-10. "
            "A conversão direta só é possível para ISBN-13 com prefixo 978 "
            "e dígito verificador válido."
        )
        print(f"[TEMPO] Conversão ISBN: {tempo_conversao:.4f} segundos")
        print(f"[TEMPO] Fluxo total: {time.perf_counter() - inicio_total:.2f} segundos")
        return None

    print(f"ISBN-10 calculado: {isbn10}")
    print(f"ASIN potencial:    {isbn10}")

    url_brasil = f"https://www.amazon.com.br/dp/{isbn10}"

    print(f"URL gerada:        {url_brasil}")
    print("\nConsultando a página na Amazon Brasil...\n")
    print(f"[TEMPO] Conversão ISBN-13 -> ISBN-10: {tempo_conversao:.4f} segundos")

    inicio_url = time.perf_counter()
    resposta_produto = buscar_por_url(url_brasil)
    tempo_url = time.perf_counter() - inicio_url

    print(f"[TEMPO] Etapa completa de consulta por URL: {tempo_url:.2f} segundos")

    if resposta_produto.status_code != 200:
        print(f"[TEMPO] Fluxo total: {time.perf_counter() - inicio_total:.2f} segundos")
        return resposta_produto

    try:
        resultado_produto = resposta_produto.json()
    except ValueError:
        print("A resposta da Bright Data não contém JSON válido.")
        print(f"[TEMPO] Fluxo total: {time.perf_counter() - inicio_total:.2f} segundos")
        return resposta_produto

    if isinstance(resultado_produto, list):
        produtos = resultado_produto
    else:
        produtos = [resultado_produto]

    for produto in produtos:
        if isinstance(produto, dict):
            produto["isbn_13_informado"] = isbn_limpo
            produto["isbn_10_calculado"] = isbn10
            produto["asin_potencial"] = isbn10

    # Mantém o formato de resposta esperado pelo restante do programa.
    resposta_produto._content = json.dumps(produtos).encode("utf-8")

    print(f"[TEMPO] Fluxo total da busca por ISBN: {time.perf_counter() - inicio_total:.2f} segundos")

    return resposta_produto


# =========================================================
# BUSCAR COTAÇÃO USD -> BRL
# =========================================================

def buscar_cotacao_usd():

    url = "https://api.frankfurter.dev/v2/rate/usd/brl"

    inicio = time.perf_counter()

    try:
        resposta = requests.get(
            url,
            timeout=30
        )
    finally:
        duracao = time.perf_counter() - inicio
        print(f"\n[TEMPO] Consulta da cotação: {duracao:.2f} segundos")

    if resposta.status_code != 200:
        raise RuntimeError(
            f"Erro ao consultar cotação: "
            f"{resposta.status_code}\n"
            f"{resposta.text}"
        )

    dados = resposta.json()

    return dados["rate"]


# =========================================================
# EXIBIR PRODUTO
# =========================================================

def mostrar_produto(produto, numero=None):

    print()
    print("=" * 60)

    if numero is not None:
        print(f"                    PRODUTO {numero}")
        print("=" * 60)

    titulo = produto.get("title") or produto.get("name")

    preco = produto.get("final_price")

    if preco is None:
        preco = produto.get("initial_price")

    moeda = produto.get("currency")
    disponibilidade = produto.get("availability")
    vendedor = produto.get("seller_name")
    isbn = (
        produto.get("isbn_13")
        or produto.get("isbn")
        or produto.get("isbn_13_informado")
    )
    asin = produto.get("asin") or produto.get("asin_potencial")
    url = produto.get("url")

    print(f"Título:       {titulo or 'Não informado'}")

    if preco is not None:
        try:
            preco_num = float(preco)
            if moeda == "BRL":
                print(f"Preço:        R$ {preco_num:.2f}")
            else:
                print(f"Preço:        {preco} {moeda or ''}".strip())
        except (TypeError, ValueError):
            print(f"Preço:        {preco} {moeda or ''}".strip())
    else:
        print("Preço:        Não informado")

    print(f"Moeda:        {moeda or 'Não informado'}")
    print(f"Disponível:   {disponibilidade or 'Não informado'}")
    print(f"Vendedor:     {vendedor or 'Não informado'}")
    print(f"ISBN:         {isbn or 'Não informado'}")
    print(f"ASIN retornado: {produto.get('asin') or 'Não informado'}")
    print(f"ASIN potencial: {produto.get('asin_potencial') or 'Não informado'}")
    print(f"URL:          {url or 'Não informado'}")

    print("=" * 60)

def extrair_produtos(dados_brutos: list | dict) -> list[dict]:

    if isinstance(dados_brutos, dict):
        itens = [dados_brutos]
    elif isinstance(dados_brutos, list):
        itens = dados_brutos
    else:
        return []

    ofertas_limpas = []

    for item in itens:
        if not isinstance(item, dict):
            continue

        # 2. Resgata o título / nome
        titulo = item.get("title") or item.get("name") or "Título não informado"

        # 3. Resgata o autor
        autor_bruto = item.get("author") or item.get("authors") or item.get("brand") or item.get("manufacturer")
        if isinstance(autor_bruto, list):
            nomes = [a.get("name", str(a)) if isinstance(a, dict) else str(a) for a in autor_bruto]
            autor = ", ".join(nomes) if nomes else "Autor não informado"
        elif isinstance(autor_bruto, dict):
            autor = autor_bruto.get("name") or str(autor_bruto)
        elif autor_bruto:
            autor = str(autor_bruto).strip()
        else:
            autor = "Autor não informado"

        # 4. Pega o preço correto (final_price ou initial_price) e converte para float
        preco_bruto = item.get("final_price") or item.get("initial_price")
        try:
            preco_float = float(preco_bruto) if preco_bruto is not None else 0.0
        except (ValueError, TypeError):
            preco_float = 0.0

        # 5. Resgata o link do produto
        url = item.get("url") or ""

        # 6. Monta o dicionário padronizado do Folheia
        ofertas_limpas.append({
            "loja": "Amazon",
            "titulo": titulo,
            "autor": autor,
            "preco": preco_float,
            "link": url,
            "disponibilidade": item.get("availability", "Disponível")
        })

    return ofertas_limpas


def executar_scraping_amazon(isbn: str):
    resposta = buscar_por_isbn(isbn)

    if not resposta or resposta.status_code != 200:
        return []

    
    produtos = extrair_produtos(resposta.json())

    return produtos


# =========================================================
# MENU
# =========================================================
def busca_manual():
    print("=" * 60)
    print("                    FOLHEIA")
    print("                BUSCA NA AMAZON")
    print("=" * 60)

    print()
    print("1 - Pesquisar por URL")
    print("2 - Pesquisar por ISBN-13 (conversão direta para ISBN-10)")
    print()

    modo = input("Escolha uma opção: ")

    inicio_total = time.perf_counter()


    # =========================================================
    # ESCOLHA DA BUSCA
    # =========================================================

    if modo == "1":

        print()
        url = input("Digite a URL da Amazon: ")
        print("\nConsultando a Amazon...\n")
        resposta = buscar_por_url(url)

    elif modo == "2":

        print()
        isbn = input("Digite o ISBN-13: ")
        print("\nConvertendo ISBN e consultando a Amazon...\n")
        resposta = buscar_por_isbn(isbn)

        if resposta is None:
            print("\nBusca encerrada: não foi possível gerar uma consulta válida.")
            print(
                f"[TEMPO] Tempo total do programa após a escolha: "
                f"{time.perf_counter() - inicio_total:.2f} segundos"
            )
            raise SystemExit(0)

    else:

        print("\nOpção inválida.")
        raise SystemExit(0)


    # =========================================================
    # TRATAMENTO DO RESULTADO
    # =========================================================

    if resposta.status_code != 200:

        print("=" * 60)
        print("                    ERRO")
        print("=" * 60)

        print(f"Status HTTP: {resposta.status_code}")
        print()
        print(resposta.text)

    else:

        try:
            resultado = resposta.json()
        except ValueError:
            print("A resposta não contém JSON válido.")
            print(resposta.text)
            resultado = []
        print (resposta.text)
        if isinstance(resultado, list):
            produtos = resultado
        else:
            produtos = [resultado]

        if not produtos:

            print("=" * 60)
            print("              NENHUM PRODUTO ENCONTRADO")
            print("=" * 60)

        else:

            print("=" * 60)

            if len(produtos) == 1:
                print("                 1 PRODUTO ENCONTRADO")
            else:
                print(f"                {len(produtos)} PRODUTOS ENCONTRADOS")

            print("=" * 60)

            for i, produto in enumerate(produtos, start=1):
                if isinstance(produto, dict):
                    mostrar_produto(produto, i)
                else:
                    print(f"Resultado {i}: {produto}")

            print()
            print("Busca concluída.")
            print()

    print(
        f"[TEMPO] Tempo total do programa após a escolha: "
        f"{time.perf_counter() - inicio_total:.2f} segundos"
    )