from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from core.database import get_db
from schemas.common import DadosMensagem, StatusConexao

router = APIRouter(tags=["Sistema"])

@router.get("/testar-conexao", response_model=StatusConexao)
def test_db_connection(db: Session = Depends(get_db)):
    """
    Testa a conectividade com o banco de dados RDS via SQLAlchemy.
    """
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "sucesso",
            "mensagem": "Conectado ao RDS com sucesso!"
        }
    except Exception as e:
        return {
            "status": "erro",
            "mensagem": f"Falha na conexão: {str(e)}"
        }

@router.post("/receive-message")
def receive_message(data: DadosMensagem):
    """
    Endpoint para recepção e confirmação de mensagens.
    """
    return {
        "status": "sucess",
        "received": data.mensagem
    }
