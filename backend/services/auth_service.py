from typing import Optional
from sqlalchemy.orm import Session
from core.config import EMAIL_REGEX, PERMISSOES_VALIDAS
from core.security import (
    ErroCadastro,
    ErroAutenticacao,
    gerar_hash_senha,
    verificar_senha,
    gerar_token,
)
from crud.crud_user import get_user_by_email, create_user

def register_user(
    db: Session,
    nome: str,
    email: str,
    senha_plana: str,
    permissoes: Optional[str] = None
) -> dict:
    """
    Regra de negócio para cadastro de novo usuário:
    - Validação de campos obrigatórios e formato de e-mail.
    - Validação de níveis de permissão permitidos.
    - Verificação de unicidade de e-mail no banco via ORM.
    - Hash seguro da senha via bcrypt.
    - Persistência via CRUD ORM.
    """
    nome_limpo = (nome or "").strip()
    email_limpo = (email or "").strip().lower()

    if not nome_limpo or not email_limpo or not senha_plana:
        raise ErroCadastro("Nome, e-mail e senha são obrigatórios.")

    if not EMAIL_REGEX.match(email_limpo):
        raise ErroCadastro("Formato de e-mail inválido.")

    if permissoes is not None and permissoes not in PERMISSOES_VALIDAS:
        raise ErroCadastro("Permissão inválida.")

    # Verifica se já existe um usuário cadastrado com esse e-mail
    if get_user_by_email(db, email_limpo):
        raise ErroCadastro("E-mail já cadastrado.")

    senha_hash = gerar_hash_senha(senha_plana)

    usuario = create_user(
        db=db,
        nome=nome_limpo,
        email=email_limpo,
        senha_hash=senha_hash,
        permissoes=permissoes or "usuario",
    )

    return {
        "id": usuario.id,
        "Nome": usuario.nome,
        "Email": usuario.email,
        "Permissoes": usuario.permissoes,
    }

def login_user(db: Session, email: str, senha_plana: str) -> dict:
    """
    Regra de negócio para autenticação de usuário:
    - Validação de credenciais.
    - Busca pelo usuário no banco via ORM.
    - Verificação criptográfica do hash bcrypt.
    - Emissão de token JWT com tempo de expiração.
    - Tratamento seguro de falhas com mensagem genérica (anti-enumeração).
    """
    email_limpo = (email or "").strip().lower()

    if not email_limpo or not senha_plana:
        raise ErroAutenticacao("E-mail ou senha incorretos.")

    usuario = get_user_by_email(db, email_limpo)

    if not usuario or not verificar_senha(senha_plana, usuario.senha):
        raise ErroAutenticacao("E-mail ou senha incorretos.")

    dados_publicos = {
        "id": usuario.id,
        "Nome": usuario.nome,
        "Email": usuario.email,
        "Permissoes": usuario.permissoes,
    }
    dados_publicos["token"] = gerar_token(dados_publicos)
    return dados_publicos
