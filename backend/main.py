from fastapi import FastAPI, Depends, HTTPException, status
import asyncio
import os
import re
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import bcrypt
import jwt

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
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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
async def buscarlivros(tipo: str | None = None, termo: str = "Não inserido", db = Depends(get_db)):
    
    if not termo:
        if tipo == 'titulo':
            query = text("""
                SELECT *
                FROM public.editions
                WHERE titulo ILIKE ?
                LIMIT 1
            """)
            param = f"%{termo}%"

        elif tipo == 'autor':
            query = text("""
                SELECT *
                FROM public.editions
                WHERE autor ILIKE ?
                LIMIT 1
            """)
            param = f"%{termo}%"

        elif tipo == 'isbn':
            query = text("""
                SELECT *
                FROM public.editions
                WHERE isbn = replace(?, '-', '')
                LIMIT 1
            """)
            param = f"%{termo}%"
    else:
        raise HTTPException(status_code=400, detail="Tipo de busca inválido: campo de busca vazio")

    
    try:

        resultado = db.execute(query, {"termo": param}).mappings().fetchone()
        
        if not resultado:
            raise HTTPException(status_code=404, detail=f"Nenhuma obra possui esse {termo}")
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


# =================================================================
#                    AUTENTICAÇÃO (CADASTRO / LOGIN)
# =================================================================
# Boas práticas de segurança aplicadas:
# - A senha NUNCA é armazenada em texto plano: apenas o hash bcrypt.
# - Todas as queries usam bind parameters (:param), evitando SQL Injection.
# - O login retorna erro genérico, evitando enumeração de usuários.
# =================================================================

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "troque-esta-chave-por-uma-segura-em-producao")
JWT_ALGORITHM = "HS256"
JWT_EXPIRACAO_MINUTOS = int(os.getenv("JWT_EXPIRACAO_MINUTOS", "60"))

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PERMISSOES_VALIDAS = {"usuario", "funcionario", "admin"}

# O bcrypt processa no máximo 72 bytes; entradas maiores são rejeitadas.
BCRYPT_MAX_BYTES = 72


# ------------------------- Exceções de domínio -------------------------
class ErroCadastro(Exception):
    """Falha de validação/regra de negócio no cadastro."""


class ErroAutenticacao(Exception):
    """Credenciais inválidas no login."""


# ------------------------ Utilitários de senha -------------------------
def gerar_hash_senha(senha_plana: str) -> str:
    """Gera o hash bcrypt (com salt aleatório) de uma senha em texto plano."""
    if len(senha_plana.encode("utf-8")) > BCRYPT_MAX_BYTES:
        raise ErroCadastro("A senha é muito longa (máximo de 72 bytes).")

    salt = bcrypt.gensalt()
    return bcrypt.hashpw(senha_plana.encode("utf-8"), salt).decode("utf-8")


def verificar_senha(senha_plana: str, senha_hash: str) -> bool:
    """Compara a senha em texto plano com o hash salvo no banco."""
    try:
        return bcrypt.checkpw(
            senha_plana.encode("utf-8"), senha_hash.encode("utf-8")
        )
    except (ValueError, TypeError):
        # Hash corrompido/em formato inesperado nunca deve autenticar.
        return False


def gerar_token(usuario: dict) -> str:
    """Gera um JWT simples de sessão para o usuário autenticado."""
    agora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario["id"]),
        "email": usuario["Email"],
        "permissoes": usuario["Permissoes"],
        "iat": agora,
        "exp": agora + timedelta(minutes=JWT_EXPIRACAO_MINUTOS),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


# ------------------------- RF01 - Cadastro -----------------------------
def register_user(db, nome: str, email: str, senha_plana: str,
                  permissoes: str | None = None) -> dict:
    """
    Cadastra um usuário respeitando o esquema da tabela `users`.

    - Valida campos obrigatórios e formato de e-mail.
    - Impede e-mail duplicado.
    - Armazena apenas o hash da senha (bcrypt).
    - Omite a coluna Permissoes quando não informada (herda o DEFAULT 'usuario').

    Retorna um dict com o id e os dados públicos do usuário recém-criado.
    """
    nome = (nome or "").strip()
    email = (email or "").strip().lower()

    # --- Validações básicas ---
    if not nome or not email or not senha_plana:
        raise ErroCadastro("Nome, e-mail e senha são obrigatórios.")

    if not EMAIL_REGEX.match(email):
        raise ErroCadastro("Formato de e-mail inválido.")

    if permissoes is not None and permissoes not in PERMISSOES_VALIDAS:
        raise ErroCadastro("Permissão inválida.")

    # --- Verifica colisão de e-mail (parameterized query) ---
    email_existente = db.execute(
        text("SELECT id FROM users WHERE Email = :email"),
        {"email": email},
    ).fetchone()

    if email_existente:
        raise ErroCadastro("E-mail já cadastrado.")

    # --- Hash da senha antes de persistir ---
    senha_hash = gerar_hash_senha(senha_plana)

    # --- INSERT com bind parameters ---
    if permissoes is None:
        # Omite Permissoes para herdar o DEFAULT 'usuario' do esquema.
        query = text(
            """
            INSERT INTO users (Nome, Email, Senha)
            VALUES (:nome, :email, :senha)
            RETURNING id, Permissoes AS "Permissoes"
            """
        )
        params = {"nome": nome, "email": email, "senha": senha_hash}
    else:
        query = text(
            """
            INSERT INTO users (Nome, Email, Senha, Permissoes)
            VALUES (:nome, :email, :senha, :permissoes)
            RETURNING id, Permissoes AS "Permissoes"
            """
        )
        params = {
            "nome": nome,
            "email": email,
            "senha": senha_hash,
            "permissoes": permissoes,
        }

    try:
        resultado = db.execute(query, params).mappings().fetchone()
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "id": resultado["id"],
        "Nome": nome,
        "Email": email,
        "Permissoes": resultado["Permissoes"],
    }


# ------------------------- RF02 - Login --------------------------------
def login_user(db, email: str, senha_plana: str) -> dict:
    """
    Autentica o usuário pelo e-mail e senha.

    - Busca o usuário pelo e-mail (parameterized query).
    - Compara a senha informada com o hash via bcrypt.
    - Retorna os dados públicos (sem a senha), as permissões e um token JWT.
    - Em qualquer falha, retorna erro genérico (evita enumeração de usuários).
    """
    email = (email or "").strip().lower()

    if not email or not senha_plana:
        raise ErroAutenticacao("E-mail ou senha incorretos.")

    usuario = db.execute(
        text(
            """
            SELECT
                id,
                Nome        AS "Nome",
                Email       AS "Email",
                Senha       AS "Senha",
                Permissoes  AS "Permissoes"
            FROM users
            WHERE Email = :email
            """
        ),
        {"email": email},
    ).mappings().fetchone()

    # Usuário inexistente OU senha incorreta -> mesma mensagem genérica.
    if not usuario or not verificar_senha(senha_plana, usuario["Senha"]):
        raise ErroAutenticacao("E-mail ou senha incorretos.")

    dados_publicos = {
        "id": usuario["id"],
        "Nome": usuario["Nome"],
        "Email": usuario["Email"],
        "Permissoes": usuario["Permissoes"],
    }
    dados_publicos["token"] = gerar_token(dados_publicos)
    return dados_publicos


# --------------------- Schemas das requisições HTTP --------------------
class CadastroRequest(BaseModel):
    nome: str
    email: str
    senha: str


class LoginRequest(BaseModel):
    email: str
    senha: str


# ----------------------------- Rotas -----------------------------------
@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def rota_register(payload: CadastroRequest, db=Depends(get_db)):
    try:
        usuario = register_user(db, payload.nome, payload.email, payload.senha)
    except ErroCadastro as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))

    return {"mensagem": "Usuário cadastrado com sucesso.", "usuario": usuario}


@app.post("/auth/login")
def rota_login(payload: LoginRequest, db=Depends(get_db)):
    try:
        usuario = login_user(db, payload.email, payload.senha)
    except ErroAutenticacao as erro:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(erro))

    return {"mensagem": "Login realizado com sucesso.", "usuario": usuario}


# ---------------- Exemplo curto de uso (python main.py) ---------------
if __name__ == "__main__":
    sessao = SessionLocal()
    try:
        # Cadastro
        novo = register_user(
            sessao,
            nome="Maria Silva",
            email="maria@exemplo.com",
            senha_plana="minhaSenhaSegura123",
        )
        print("Usuário criado:", novo)

        # Login
        autenticado = login_user(
            sessao,
            email="maria@exemplo.com",
            senha_plana="minhaSenhaSegura123",
        )
        print("Login OK:", autenticado)
    except (ErroCadastro, ErroAutenticacao) as erro:
        print("Erro esperado:", erro)
    finally:
        sessao.close()