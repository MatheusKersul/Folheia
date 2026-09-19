from fastapi import FastAPI, Depends, HTTPException
import asyncio
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

load_dotenv()

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

class RespostaLivros(BaseModel):
    isbn: str
    titulo: str
    data_publicacao: str | None
    formato: str | None
    num_paginas: int | None
    editora: str | None
    autor: str | None


class RespostaBusca(BaseModel):
    isbn: str
    ofertas: list[OfertaLivro]

#===============CONFIGURAÇÃO DO BANCO DE DADOS RDS===============

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind = engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

#================================================================

@app.get("/testar-conexao")
def test_db_connection(db = Depends(get_db)):
    try:
        
        db.execute(text("SELECT 1"))
        return {"status": "sucesso", "mensagem": "Conectado ao RDS com sucesso!"}
    except Exception as e:
        return {"status": "erro", "mensagem": f"Falha na conexão: {str(e)}"}

@app.get("/buscar-livros", response_model=RespostaLivros)
async def buscarlivros(isbn: str | None = None, titulo: str = "Não informado", db = Depends(get_db)):
    await asyncio.sleep(2)

    try:
        query = text("""
            SELECT *
            FROM public.editions
            WHERE isbn_13 = :isbn
            LIMIT 1
        """)

        resultado = db.execute(
            query,
            {"isbn": isbn}
        ).mappings().fetchone()

        if not resultado:
            query = text("""
                SELECT *
                FROM public.editions
                WHERE titulo ILIKE :titulo
                LIMIT 1
            """)

            resultado = db.execute(
                query,
                {"titulo": f"%{titulo}%"}
            ).mappings().fetchone()

        if not resultado:
            raise HTTPException(status_code=404, detail="Nenhuma obra possui esse titulo ou isbn")
        else:
            return RespostaLivros(
                isbn=resultado["isbn_13"], titulo=resultado["titulo"],
                data_publicacao=resultado["data_publicacao"], formato=resultado["formato"],
                num_paginas=resultado["num_paginas"], editora=resultado["editora"],
                autor=resultado["autor"]
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@app.get("/buscar-precos/{termo_busca}", response_model=RespostaBusca)
async def buscarprecos(termo_busca: str, isbn: str = "Não informado"):
    await asyncio.sleep(5)
    #simulação da requisão do frontend e resposta do postgre
    ofertas_encontradas = [
        OfertaLivro(loja="Mercado livre", preco=45.90, link="linkmercadolivre"),
        OfertaLivro(loja="Shopee", preco=35.90, link="linkshopee"),
        OfertaLivro(loja="Amazon", preco=55.90, link="https://www.amazon.com.br/FRANKENSTEIN-OUTRAS-HIST%C3%93RIAS-HORROR-JUNJI-ebook/dp/B09HW2WTPR/?_encoding=UTF8&pd_rd_w=onFf5&content-id=amzn1.sym.761077be-03f4-471e-82eb-e510d48b59aa&pf_rd_p=761077be-03f4-471e-82eb-e510d48b59aa&pf_rd_r=WK9S1AT5SMMGW55AZSBS&pd_rd_wg=X6CGY&pd_rd_r=53299eca-1dc5-4de8-aa92-7270946f9c75&ref_=pd_hp_d_r_atf_mtech-exp-p13ndeals")
    ]

    return RespostaBusca(titulo = termo_busca, isbn = isbn, ofertas=ofertas_encontradas)

class Dadosmensagem(BaseModel):
    mensagem: str

@app.post("/receive-message")
def receive_message(data: Dadosmensagem):
    return {"status": "sucess", "received": data.mensagem}