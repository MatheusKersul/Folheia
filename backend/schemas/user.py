from pydantic import BaseModel, ConfigDict, EmailStr

class CadastroRequest(BaseModel):
    """Esquema de requisição para novo cadastro de usuário."""
    nome: str
    email: str
    senha: str


class LoginRequest(BaseModel):
    """Esquema de requisição para autenticação de usuário."""
    email: str
    senha: str


class UsuarioResponse(BaseModel):
    """Esquema de dados públicos do usuário retornado pela API."""
    id: int
    Nome: str
    Email: str
    Permissoes: str

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class UsuarioComTokenResponse(UsuarioResponse):
    """Esquema de dados do usuário autenticado acompanhado de seu token JWT."""
    token: str


class RespostaCadastro(BaseModel):
    """Resposta padrão da rota de cadastro."""
    mensagem: str
    usuario: dict


class RespostaLogin(BaseModel):
    """Resposta padrão da rota de login."""
    mensagem: str
    usuario: dict
