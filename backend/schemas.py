"""
Modelos de entrada e saída do Pydantic para validação e serialização de dados da API.
"""
from schemas.user import (
    CadastroRequest,
    LoginRequest,
    UsuarioResponse,
    UsuarioComTokenResponse,
    RespostaCadastro,
    RespostaLogin,
)
from schemas.book import OfertaLivro, RespostaLivros, RespostaBusca
from schemas.library import (
    AdicionarLivroRequest,
    BibliotecaResumo,
    CriarEdicaoPropriaRequest,
    EdicaoBiblioteca,
    ItemBiblioteca,
    RespostaBiblioteca,
    RespostaEdicoesProprias,
)
from schemas.common import DadosMensagem, Dadosmensagem, StatusConexao

__all__ = [
    "CadastroRequest",
    "LoginRequest",
    "UsuarioResponse",
    "UsuarioComTokenResponse",
    "RespostaCadastro",
    "RespostaLogin",
    "OfertaLivro",
    "RespostaLivros",
    "RespostaBusca",
    "AdicionarLivroRequest",
    "BibliotecaResumo",
    "CriarEdicaoPropriaRequest",
    "EdicaoBiblioteca",
    "ItemBiblioteca",
    "RespostaBiblioteca",
    "RespostaEdicoesProprias",
    "DadosMensagem",
    "Dadosmensagem",
    "StatusConexao",
]
