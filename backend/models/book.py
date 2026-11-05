from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import relationship
from core.database import Base


class Edition(Base):
    """
    Modelo ORM que mapeia a tabela 'editions' no PostgreSQL.

    Uma edição pode ser:
    - oficial/verificada (``verificada=True``), carregada do catálogo OpenLibrary;
    - própria do usuário (``verificada=False``), criada manualmente e visível
      apenas para o usuário que a registrou (``id_usuario_criador``).
    """

    __tablename__ = "editions"
    __table_args__ = (
        CheckConstraint(
            "verificada OR id_usuario_criador IS NOT NULL",
            name="ck_editions_privada_tem_dono",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    # ISBN é opcional: edições próprias podem não possuir ISBN.
    isbn_13 = Column(String(13), nullable=True, index=True)
    titulo = Column(Text, nullable=True, index=True)
    data_publicacao = Column(String(255), nullable=True)
    formato = Column(String(255), nullable=True)
    num_paginas = Column(Integer, nullable=True)
    editora = Column(Text, nullable=True)
    autor = Column(Text, nullable=True, index=True)

    # TRUE = catálogo oficial; FALSE = edição própria (não verificada).
    verificada = Column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    # Dono da edição própria; NULL nas edições oficiais.
    id_usuario_criador = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    links = relationship("LinkLibrary", back_populates="livro")
    criador = relationship("User", back_populates="edicoes_criadas")

    @property
    def propria(self) -> bool:
        """Indica se a edição foi criada por um usuário (não oficial)."""
        return self.id_usuario_criador is not None

    def __repr__(self) -> str:
        titulo = self.titulo[:30] if self.titulo else "Sem título"
        return f"<Edition(isbn={self.isbn_13}, titulo={titulo}, verificada={self.verificada})>"
