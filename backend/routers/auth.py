from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import ErroCadastro, ErroAutenticacao
from schemas.user import CadastroRequest, LoginRequest
from services.auth_service import register_user, login_user

router = APIRouter(tags=["Autenticação"])

@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
def rota_register(payload: CadastroRequest, db: Session = Depends(get_db)):
    """
    Cadastra um novo usuário no sistema.
    Retorna os dados públicos do usuário criado.
    """
    try:
        usuario = register_user(
            db=db,
            nome=payload.nome,
            email=payload.email,
            senha_plana=payload.senha,
        )
    except ErroCadastro as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )

    return {"mensagem": "Usuário cadastrado com sucesso.", "usuario": usuario}


@router.post("/auth/login")
def rota_login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Autentica o usuário por e-mail e senha.
    Retorna os dados do usuário e o token JWT de sessão.
    """
    try:
        usuario = login_user(
            db=db,
            email=payload.email,
            senha_plana=payload.senha,
        )
    except ErroAutenticacao as erro:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(erro)
        )

    return {"mensagem": "Login realizado com sucesso.", "usuario": usuario}
