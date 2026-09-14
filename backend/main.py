from fastapi import FastAPI
import asyncio
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="API Folheia", description="Sistema de busca de preço de livros")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Trocar para a url posteriormente
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class OfertaLivro(BaseModel):
    loja: str
    preco: float
    link: str

class RespostaBusca(BaseModel):
    isbn: str
    ofertas: list[OfertaLivro]

@app.get("/buscar-precos/{termo_busca}", response_model=RespostaBusca)
async def buscarprecos(termo_busca: str, isbn: str = "Não informado"):
    await asyncio.sleep(5)
    #simulação da requisão do frontend e resposta do postgre
    ofertas_encontradas = [
        OfertaLivro(loja="Mercado livre", preco=45.90, link="linkmercadolivre"),
        OfertaLivro(loja="Shopee", preco=35.90, link="linkshopee"),
        OfertaLivro(loja="Amazon", preco=55.90, link="linkamazon")
    ]

    return RespostaBusca(titulo = termo_busca, isbn = isbn, ofertas=ofertas_encontradas)

class Dadosmensagem(BaseModel):
    mensagem: str

@app.post("/receive-message")
def receive_message(data: Dadosmensagem):
    return {"status": "sucess", "received": data.mensagem}