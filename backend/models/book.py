from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship
from core.database import Base

class Edition(Base):

    __tablename__ = "editions"

    id = Column(Integer, primary_key=True, index=True)
    isbn_13 = Column(String(13), unique=True, nullable=False, index=True)
    titulo = Column(Text, nullable=True, index=True)
    data_publicacao = Column(String(255), nullable=True)
    formato = Column(String(255), nullable=True)
    num_paginas = Column(Integer, nullable=True)
    editora = Column(Text, nullable=True)
    autor = Column(Text, nullable=True, index=True)

    links = relationship("LinkLibrary", back_populates="livro")

    def __repr__(self) -> str:
        return f"<Edition(isbn={self.isbn_13}, titulo={self.titulo[:30] if self.titulo else 'Sem título'})>"
