import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class BibliotecaResumo(BaseModel):
    """Identificação da biblioteca pessoal à qual o item pertence."""

    id: int
    nome: str

    model_config = {"from_attributes": True}


class EdicaoBiblioteca(BaseModel):
    """
    Dados de uma edição exibidos na biblioteca do usuário.

    ``verificada=False`` indica edição própria (não oficial), visível
    apenas para quem a registrou.
    """

    id: int
    isbn: Optional[str] = None
    titulo: str
    data_publicacao: Optional[str] = None
    formato: Optional[str] = None
    num_paginas: Optional[int] = None
    editora: Optional[str] = None
    autor: Optional[str] = None
    verificada: bool
    propria: bool

    @classmethod
    def from_edition(cls, edition) -> "EdicaoBiblioteca":
        return cls(
            id=edition.id,
            isbn=edition.isbn_13,
            titulo=edition.titulo or "",
            data_publicacao=edition.data_publicacao,
            formato=edition.formato,
            num_paginas=edition.num_paginas,
            editora=edition.editora,
            autor=edition.autor,
            verificada=bool(edition.verificada),
            propria=edition.propria,
        )


class ItemBiblioteca(BaseModel):
    """Item (vínculo) entre a biblioteca do usuário e uma edição."""

    id: int
    criado_em: Optional[datetime] = None
    biblioteca: BibliotecaResumo
    edicao: EdicaoBiblioteca

    @classmethod
    def from_link(cls, link) -> "ItemBiblioteca":
        return cls(
            id=link.id,
            criado_em=link.criado_em,
            biblioteca=BibliotecaResumo(id=link.biblioteca.id, nome=link.biblioteca.nome),
            edicao=EdicaoBiblioteca.from_edition(link.livro),
        )


class RespostaBiblioteca(BaseModel):
    """Listagem paginada da biblioteca pessoal."""

    total: int
    page: int
    limit: int
    itens: list[ItemBiblioteca]


class RespostaEdicoesProprias(BaseModel):
    """Listagem paginada das edições próprias (não verificadas) do usuário."""

    total: int
    page: int
    limit: int
    edicoes: list[EdicaoBiblioteca]


class AdicionarLivroRequest(BaseModel):
    """
    Identifica a obra do catálogo a ser adicionada à biblioteca.

    Informe exatamente um dos campos: ``edition_id`` ou ``isbn``.
    """

    edition_id: Optional[int] = Field(default=None, ge=1)
    isbn: Optional[str] = None

    @model_validator(mode="after")
    def validar_identificador(self) -> "AdicionarLivroRequest":
        tem_id = self.edition_id is not None
        tem_isbn = bool(self.isbn and self.isbn.strip())

        if tem_id == tem_isbn:
            raise ValueError(
                "Informe exatamente um identificador: 'edition_id' ou 'isbn'."
            )
        return self


class CriarEdicaoPropriaRequest(BaseModel):
    """
    Dados de uma edição criada pelo próprio usuário.

    A edição resultante é marcada como ``verificada=False`` e fica visível
    apenas para quem a cadastrou.
    """

    titulo: str = Field(min_length=1, max_length=500)
    autor: Optional[str] = Field(default=None, max_length=500)
    isbn: Optional[str] = None
    data_publicacao: Optional[str] = Field(default=None, max_length=255)
    formato: Optional[str] = Field(default=None, max_length=255)
    num_paginas: Optional[int] = Field(default=None, ge=1, le=100000)
    editora: Optional[str] = Field(default=None, max_length=500)

    @field_validator("titulo")
    @classmethod
    def validar_titulo(cls, valor: str) -> str:
        titulo = (valor or "").strip()
        if not titulo:
            raise ValueError("O título é obrigatório.")
        return titulo

    @field_validator("autor", "data_publicacao", "formato", "editora")
    @classmethod
    def normalizar_opcionais(cls, valor: Optional[str]) -> Optional[str]:
        if valor is None:
            return None
        texto = valor.strip()
        return texto or None

    @field_validator("isbn")
    @classmethod
    def normalizar_isbn(cls, valor: Optional[str]) -> Optional[str]:
        if valor is None:
            return None
        digitos = re.sub(r"\D", "", valor)
        if not digitos:
            return None
        if len(digitos) != 13:
            raise ValueError("O ISBN deve conter exatamente 13 dígitos.")
        return digitos
