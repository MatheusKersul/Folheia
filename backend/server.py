import sys
from pathlib import Path

# Garante que o diretório backend esteja no sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.database import SessionLocal, get_db
from core.security import ErroCadastro, ErroAutenticacao
from services.auth_service import register_user, login_user
from routers import auth_router, books_router, system_router

# Inicialização da aplicação FastAPI
app = FastAPI(
    title="API Folheia",
    description="Sistema de busca e comparação de preços de livros com acervo bibliográfico",
    version="1.0.0",
)

# Configuração de CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configurar origens específicas em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusão dos roteadores modulares
app.include_router(system_router)
app.include_router(books_router)
app.include_router(auth_router)


if __name__ == "__main__":
    sessao = SessionLocal()
    try:
        print("Executando teste local do fluxo de autenticação...")
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
        print("Resultado/Erro esperado:", erro)
    except Exception as e:
        print("Exceção:", e)
    finally:
        sessao.close()