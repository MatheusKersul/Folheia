from fastapi import FastAPI
import asyncio
from pydantic import BaseModel

app = FastAPI(title="API Folheia", description="Sistema de busca de preço de livros")

class OfertaLivro(BaseModel):
    loja: str
    preco: float
    link: str

class RespostaBusca(BaseModel):
    isbn: str
    ofertas: list[OfertaLivro]

@app.get("/buscar-precos/{termo_busca}", response_model=RespostaBusca)
async def buscarprecos(titulo = str, isbn = str):
    await asyncio.sleep(2)
    #simulação da requisão do frontend e resposta do postgre
    ofertas_encontradas = [
        OfertaLivro(loja="Mercado livre", preco=45.90, link="linkmercadolivre"),
        OfertaLivro(loja="Shopee", preco=35.90, link="linkshopee"),
        OfertaLivro(loja="Amazon", preco=55.90, link="linkamazon")
    ]

    return RespostaBusca(titulo = titulo, isbn = isbn, ofertas=ofertas_encontradas)