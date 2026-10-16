from typing import Optional
from pydantic import BaseModel, ConfigDict

class OfertaLivro(BaseModel):
    """Representa a oferta de preço de um livro em determinado e-commerce."""
    loja: str
    preco: float
    link: str


class RespostaLivros(BaseModel):
    """
    Representa as informações bibliográficas consolidadas de um livro
    retornadas para o cliente (busca por título, autor ou ISBN).
    """
    isbn: str
    titulo: str
    data_publicacao: Optional[str] = None
    formato: Optional[str] = None
    num_paginas: Optional[int] = None
    editora: Optional[str] = None
    autor: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_edition(cls, edition) -> "RespostaLivros":
        """Converte uma entidade Edition (ORM) no schema RespostaLivros."""
        return cls(
            isbn=edition.isbn_13,
            titulo=edition.titulo or "",
            data_publicacao=edition.data_publicacao,
            formato=edition.formato,
            num_paginas=edition.num_paginas,
            editora=edition.editora,
            autor=edition.autor,
        )


class RespostaBusca(BaseModel):
    """Representa o resultado da busca de preços com lista de ofertas."""
    isbn: str = "Não informado"
    titulo: Optional[str] = None
    ofertas: list[OfertaLivro]
