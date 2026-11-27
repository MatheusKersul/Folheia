from typing import Optional, List
from pydantic import BaseModel, Field

class OfertaScrap(BaseModel):
    loja: str = Field(..., example="Amazon", description="Nome da loja parceira")
    titulo: Optional[str] = Field(None, example="Frankenstein, ou o Prometeu Moderno", description="Título / Nome da obra")
    autor: Optional[str] = Field(None, example="Mary Shelley", description="Autor da obra")
    preco: float = Field(..., example=49.90, description="Preço atual do livro em BRL")
    link: str = Field(..., example="https://www.amazon.com.br/dp/...", description="Link direto para a oferta")
    disponibilidade: Optional[str] = Field("Em estoque", example="Em estoque")
    isbn_13: Optional[str] = Field(None, example="9788576573005", description="ISBN-13 limpo (apenas dígitos)")
    editora: Optional[str] = Field(None, example="Aleph", description="Editora da obra")
    data_publicacao: Optional[str] = Field(None, example="19 agosto 2016", description="Data de publicação da edição")
    formato: Optional[str] = Field(None, example="Capa comum", description="Formato / acabamento da edição")
    num_paginas: Optional[int] = Field(None, example=320, description="Número de páginas da edição")
    images_url: Optional[str] = Field(None, example="https://m.media-amazon.com/images/I/91Bx5ilP+EL._SL1500_.jpg", description="URL da imagem de capa")

class ScrapeStatusResponse(BaseModel):
    isbn: str = Field(..., example="9788594540188")
    status: str = Field(..., example="concluido", description="Status: 'pendente', 'em_processamento', 'concluido' ou 'falha'")
    em_processamento: bool = Field(..., example=False)
    ofertas: List[OfertaScrap] = Field(default_factory=list, description="Lista de ofertas encontradas pelos scrapers")
