from typing import Optional, List
from pydantic import BaseModel, Field

class OfertaScrap(BaseModel):
    loja: str = Field(..., example="Amazon", description="Nome da loja parceira")
    titulo: Optional[str] = Field(None, example="Frankenstein, ou o Prometeu Moderno", description="Título / Nome da obra")
    autor: Optional[str] = Field(None, example="Mary Shelley", description="Autor da obra")
    preco: float = Field(..., example=49.90, description="Preço atual do livro em BRL")
    link: str = Field(..., example="https://www.amazon.com.br/dp/...", description="Link direto para a oferta")
    disponibilidade: Optional[str] = Field("Em estoque", example="Em estoque")

class ScrapeStatusResponse(BaseModel):
    isbn: str = Field(..., example="9788594540188")
    status: str = Field(..., example="concluido", description="Status: 'pendente', 'em_processamento', 'concluido' ou 'falha'")
    em_processamento: bool = Field(..., example=False)
    ofertas: List[OfertaScrap] = Field(default_factory=list, description="Lista de ofertas encontradas pelos scrapers")
