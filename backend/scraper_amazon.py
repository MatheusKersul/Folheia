import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BRIGHTDATA_API_KEY")

# Temporariamente, para verificar se a chave da API foi carregada corretamente
print("Chave carregada:", bool(API_KEY)) 

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

DATASET_ID = "gd_lwhideng15g8jg63s7"

# =========================================================
#                  BUSCA POR URL
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

    return requests.post(
        endpoint,
        params=params,
        headers=HEADERS,
        json=dados,
        timeout=120
    )

# =========================================================
#           BUSCA POR ISBN
# =========================================================

def buscar_por_isbn(isbn):

    endpoint = (
        "https://api.brightdata.com/datasets/v3/scrape"
        "?dataset_id=gd_l7q7dkf244hwjntr0"
        "&notify=false"
        "&include_errors=true"
        "&type=discover_new"
        "&discover_by=keyword"
    )

    dados = {
        "input": [
            {
                "keyword": isbn,
                "zipcode": ""
            }
        ],
        "limit_per_input": None
    }

    resposta = requests.post(
        endpoint,
        headers=HEADERS,
        json=dados,
        timeout=120
    )

    if resposta.status_code != 200:
        return resposta

    resultado = resposta.json()

    if isinstance(resultado, list):
        produtos = resultado
    else:
        produtos = [resultado]

    if not produtos:
        return resposta

    produto = produtos[0]

    asin = produto.get("asin")

    if not asin:
        return resposta

    url_brasil = f"https://www.amazon.com.br/dp/{asin}"

    print()
    print(f"ISBN-13 buscado: {isbn}")
    print(f"ASIN encontrado: {asin}")
    print(f"Consultando Amazon Brasil: {url_brasil}")
    print()

    resposta_produto = buscar_por_url(url_brasil)

    if resposta_produto.status_code != 200:
        return resposta_produto

    resultado_produto = resposta_produto.json()

    if isinstance(resultado_produto, list):
        produtos = resultado_produto
    else:
        produtos = [resultado_produto]

    for produto in produtos:
        produto["isbn_13"] = isbn

    resposta_produto._content = json.dumps(produtos).encode("utf-8")

    return resposta_produto
# =========================================================
#                BUSCAR COTAÇÃO USD -> BRL
# =========================================================

def buscar_cotacao_usd():

    url = "https://api.frankfurter.dev/v2/rate/usd/brl"

    resposta = requests.get(
        url,
        timeout=30
    )

    if resposta.status_code != 200:
        raise RuntimeError(
            f"Erro ao consultar cotação: "
            f"{resposta.status_code}\n"
            f"{resposta.text}"
        )

    dados = resposta.json()

    return dados["rate"]


# =========================================================
#                    EXIBIR PRODUTO
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
    isbn = produto.get("isbn_13") or produto.get("isbn")
    asin = produto.get("asin")
    url = produto.get("url")

# -----------------------------------------------------
#                      EXIBIÇÃO
# -----------------------------------------------------

    print(f"Título:       {titulo or 'Não informado'}")

    if preco is not None:
        if moeda == "BRL":
            print(f"Preço:        R$ {preco:.2f}")
        else:
            print(f"Preço:        {preco} {moeda or ''}".strip())
    else:
        print("Preço:        Não informado")

    print(f"Moeda:        {moeda or 'Não informado'}")
    print(f"Disponível:   {disponibilidade or 'Não informado'}")
    print(f"Vendedor:     {vendedor or 'Não informado'}")
    print(f"ISBN:         {isbn or 'Não informado'}")
    print(f"ASIN:         {asin or 'Não informado'}")
    print(f"URL:          {url or 'Não informado'}")

    print("=" * 60)


# =========================================================
#                           MENU
# =========================================================

print("=" * 60)
print("                    FOLHEIA")
print("                BUSCA NA AMAZON")
print("=" * 60)

print()
print("1 - Pesquisar por URL")
print("2 - Pesquisar por ISBN")
print()

modo = input("Escolha uma opção: ")


# =========================================================
#                   ESCOLHA DA BUSCA
# =========================================================

if modo == "1":

    print()

    url = input("Digite a URL da Amazon: ")

    print()
    print("Consultando a Amazon...")
    print()

    resposta = buscar_por_url(url)


elif modo == "2":

    print()

    isbn = input("Digite o ISBN: ")

    print()
    print("Procurando pelo ISBN...")
    print()

    resposta = buscar_por_isbn(isbn)


else:

    print()
    print("Opção inválida.")
    exit()


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

    resultado = resposta.json()

    if isinstance(resultado, list):

        produtos = resultado

    else:

        produtos = [resultado]

    # =====================================================
    # PRODUTOS ENCONTRADOS
    # =====================================================

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

            mostrar_produto(
                produto,
                i
            )

        print()
        print("Busca concluída.")
        print()