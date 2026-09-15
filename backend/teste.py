import os
from fastapi import FastAPI, Depends
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 1. Carrega as variáveis do arquivo .env
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# 2. Monta a URL de conexão
# ATENÇÃO: Troque "postgresql" por "mysql+pymysql" se o seu RDS for MySQL
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 3. Configura o motor do banco de dados (Engine)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI()

# 4. Cria uma dependência para abrir e fechar a conexão a cada requisição
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 5. Rota simples para testar se o banco está online e conectado
@app.get("/testar-conexao")
def test_db_connection(db = Depends(get_db)):
    try:
        # Tenta executar uma query muito simples ("SELECT 1")
        db.execute(text("SELECT 1"))
        return {"status": "sucesso", "mensagem": "Conectado ao RDS com sucesso!"}
    except Exception as e:
        return {"status": "erro", "mensagem": f"Falha na conexão: {str(e)}"}