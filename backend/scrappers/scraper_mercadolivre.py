import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BRIGHTDATA_API_KEY")

DATASET_ID = "gd_m7re62tb1w88ymy86r"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# =========================================================
#                  BUSCA POR URL NO BRIGHT DATA
# =========================================================

def buscar_por_url(url_produto):
    endpoint = "https://api.brightdata.com/datasets/v3/scrape"

    parametros = {
        "dataset_id": DATASET_ID,
        "notify": "false",
        "include_errors": "true",
    }

    dados = {
        "input": [
            {"url": url_produto}
        ],
        "limit_per_input": None,
    }

    return requests.post(
        endpoint,
        params=parametros,
        headers=HEADERS,
        json=dados,
        timeout=120,
    )


# =========================================================
#              BUSCA DE ANÚNCIOS PELO ISBN
# =========================================================


def buscar_urls_por_isbn(isbn):
    import requests
    from bs4 import BeautifulSoup

    isbn_limpo = isbn.strip().replace("-", "").replace(" ", "")
    url_busca = f"https://lista.mercadolivre.com.br/{isbn_limpo}"

    print(f"\nURL montada: {url_busca}")

    resposta = requests.get(
        url_busca,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/130.0.0.0 Safari/537.36"
            )
        },
        timeout=30,
    )

    print(f"Status HTTP: {resposta.status_code}")
    print(f"URL final: {resposta.url}")
    print(f"Tamanho do HTML: {len(resposta.text)} caracteres")
    print(f"Tipo de conteúdo: {resposta.headers.get('Content-Type')}")

    soup = BeautifulSoup(resposta.text, "html.parser")

    print(f"Elementos de resultado encontrados: "
          f"{len(soup.select('li.ui-search-layout__item'))}")
    print(f"Links de título encontrados: "
          f"{len(soup.select('a.poly-component__title, a.ui-search-link'))}")

    print("\nInício do título da página:")
    print(soup.title.get_text(" ", strip=True) if soup.title else "(sem título)")

    print("\nTrecho inicial do HTML recebido:")
    print(resposta.text[:1200])

    return []

# =========================================================
#            EXTRAIR CARACTERÍSTICA DO LIVRO
# =========================================================

def buscar_caracteristica(produto, nome):
    caracteristicas = produto.get("product_features") or []

    for caracteristica in caracteristicas:
        tipo = caracteristica.get("type", "")

        if tipo.casefold() == nome.casefold():
            return caracteristica.get("value")

    return None


# =========================================================
#                   EXIBIR PRODUTO
# =========================================================

def mostrar_produto(produto, numero=None, isbn_pesquisado=None):
    print()
    print("=" * 65)

    if numero is not None:
        print(f"                      PRODUTO {numero}")
        print("=" * 65)

    titulo = produto.get("title")
    preco = produto.get("final_price")
    preco_original = produto.get("original_price")
    moeda = produto.get("currency")
    desconto = produto.get("discount_percentage")
    disponivel = produto.get("in_stock")
    parcelas = produto.get("installments")
    frete = produto.get("shipping")
    url = produto.get("url")
    identificador = (
        produto.get("product_id")
        or produto.get("catalog_product_id")
    )
    vendedor = produto.get("seller_name")

    autor = buscar_caracteristica(produto, "Autor")
    editora = buscar_caracteristica(produto, "Editora do livro")
    formato = buscar_caracteristica(produto, "Capa do livro")
    paginas = buscar_caracteristica(produto, "Quantidade páginas")
    ano = buscar_caracteristica(produto, "Ano de publicação")
    idioma = buscar_caracteristica(produto, "Idioma")
    edicao = buscar_caracteristica(produto, "Edição do livro")
    serie = buscar_caracteristica(produto, "Série")

    isbn_retornado = (
        produto.get("isbn_13")
        or produto.get("isbn")
        or buscar_caracteristica(produto, "ISBN")
    )

    isbn = isbn_retornado or isbn_pesquisado

    print(f"Título:          {titulo or 'Não informado'}")

    if preco is not None:
        print(f"Preço:           {moeda or ''} {preco:.2f}".strip())
    else:
        print("Preço:           Não informado")

    if preco_original is not None:
        print(
            f"Preço original:  {moeda or ''} "
            f"{preco_original:.2f}".strip()
        )

    if desconto is not None:
        print(f"Desconto:        {desconto}%")

    if disponivel is True:
        texto_disponibilidade = "Sim"
    elif disponivel is False:
        texto_disponibilidade = "Não"
    else:
        texto_disponibilidade = "Não informado"

    print(f"Disponível:      {texto_disponibilidade}")
    print(f"Vendedor:        {vendedor or 'Não informado'}")
    print(f"ISBN:            {isbn or 'Não informado'}")

    if isbn_retornado is None and isbn_pesquisado:
        print("                 (ISBN pesquisado; não confirmado no anúncio)")

    print(f"Identificador:   {identificador or 'Não informado'}")
    print(f"Autor:           {autor or 'Não informado'}")
    print(f"Editora:         {editora or 'Não informado'}")
    print(f"Formato:         {formato or 'Não informado'}")
    print(f"Páginas:         {paginas or 'Não informado'}")
    print(f"Ano:             {ano or 'Não informado'}")
    print(f"Idioma:          {idioma or 'Não informado'}")
    print(f"Edição:          {edicao or 'Não informado'}")
    print(f"Série:           {serie or 'Não informado'}")
    print(f"Parcelamento:    {parcelas or 'Não informado'}")

    if isinstance(frete, list):
        texto_frete = ", ".join(str(item) for item in frete)
    elif frete:
        texto_frete = str(frete)
    else:
        texto_frete = "Não informado"

    print(f"Frete:           {texto_frete}")
    print(f"URL:             {url or 'Não informado'}")
    print("=" * 65)


# =========================================================
#               INTERPRETAR RESPOSTA DO SCRAPER
# =========================================================

def interpretar_resposta(resposta):
    if resposta.status_code != 200:
        print("=" * 65)
        print("                         ERRO")
        print("=" * 65)
        print(f"Status HTTP: {resposta.status_code}")
        print(resposta.text)
        return []

    try:
        resultado = resposta.json()
    except ValueError:
        print("A API não retornou um JSON válido.")
        print(resposta.text)
        return []

    if isinstance(resultado, list):
        produtos = resultado
    elif isinstance(resultado, dict):
        if resultado.get("error") or resultado.get("error_code"):
            print("A API retornou um erro:")
            print(resultado)
            return []

        produtos = [resultado]
    else:
        print("Formato de resposta inesperado.")
        print(resultado)
        return []

    return [
        produto
        for produto in produtos
        if isinstance(produto, dict)
        and (produto.get("title") or produto.get("product_id"))
    ]


# =========================================================
#                 BUSCA POR URL
# =========================================================

def executar_busca_url():
    url = input("Cole a URL do anúncio: ").strip()

    if not url:
        print("Nenhuma URL informada.")
        return

    print("\nConsultando o Mercado Livre pelo Bright Data...\n")

    try:
        resposta = buscar_por_url(url)
    except requests.RequestException as erro:
        print(f"Erro ao consultar o Bright Data: {erro}")
        return

    produtos = interpretar_resposta(resposta)
    exibir_resultados(produtos)

# =========================================================
#                 BUSCA POR ISBN
# =========================================================

def executar_busca_isbn():
    isbn = input("Digite o ISBN do livro: ").strip()

    if not isbn:
        print("Nenhum ISBN informado.")
        return

    print("\nProcurando anúncios no Mercado Livre...\n")

    try:
        anuncios = buscar_urls_por_isbn(isbn)
    except (requests.RequestException, RuntimeError) as erro:
        print(f"Erro na busca por ISBN: {erro}")
        return

    if not anuncios:
        print("Nenhum anúncio foi encontrado para esse ISBN.")
        return

    print(f"{len(anuncios)} anúncio(s) encontrado(s) na pesquisa inicial.")

    for i, anuncio in enumerate(anuncios, start=1):
        print(f"\n{i}. {anuncio['titulo']}")
        print(f"   URL: {anuncio['url']}")

    confirmacao = input(
        "\nConsultar os detalhes desses anúncios pelo Bright Data? (s/n): "
    ).strip().lower()

    if confirmacao != "s":
        print("Consulta detalhada cancelada.")
        return

    produtos_encontrados = []

    for i, anuncio in enumerate(anuncios, start=1):
        print(f"\nConsultando anúncio {i} de {len(anuncios)}...")

        try:
            resposta = buscar_por_url(anuncio["url"])
        except requests.RequestException as erro:
            print(f"Erro ao consultar este anúncio: {erro}")
            continue

        produtos = interpretar_resposta(resposta)

        for produto in produtos:
            produtos_encontrados.append((produto, isbn))

    if not produtos_encontrados:
        print("\nNenhum anúncio teve os detalhes coletados com sucesso.")
        return

    print()
    print("=" * 65)
    print(f"              {len(produtos_encontrados)} RESULTADO(S)")
    print("=" * 65)

    for i, (produto, isbn_pesquisado) in enumerate(
        produtos_encontrados,
        start=1,
    ):
        mostrar_produto(
            produto,
            numero=i,
            isbn_pesquisado=isbn_pesquisado,
        )

    print("\nBusca concluída.")

# =========================================================
#                EXIBIR RESULTADOS
# =========================================================

def exibir_resultados(produtos):
    if not produtos:
        print("Nenhum produto válido foi encontrado.")
        return

    print("=" * 65)

    if len(produtos) == 1:
        print("                   1 PRODUTO ENCONTRADO")
    else:
        print(f"                  {len(produtos)} PRODUTOS ENCONTRADOS")

    print("=" * 65)

    for i, produto in enumerate(produtos, start=1):
        mostrar_produto(produto, numero=i)

    print("\nBusca concluída.")

# =========================================================
#                         MENU
# =========================================================

def main():
    print("=" * 65)
    print("                         FOLHEIA")
    print("                  BUSCA NO MERCADO LIVRE")
    print("=" * 65)
    print()
    print("1 - Pesquisar por URL")
    print("2 - Pesquisar por ISBN")
    print()

    if not API_KEY:
        print("ERRO: BRIGHTDATA_API_KEY não foi encontrada no .env.")
        return

    modo = input("Escolha uma opção: ").strip()

    if modo == "1":
        executar_busca_url()
    elif modo == "2":
        executar_busca_isbn()
    else:
        print("Opção inválida.")

if __name__ == "__main__":
    main()