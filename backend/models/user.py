from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, synonym
from core.database import Base

class User(Base):
    """
    Modelo ORM que mapeia a tabela 'users' no PostgreSQL.
    Armazena credenciais e permissões dos usuários.
    Possui sinônimos para suportar tanto notação camelCase/capitalizada (Nome, Email)
    quanto snake_case (nome, email).
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column("nome", String(255), nullable=False)
    email = Column("email", String(255), unique=True, nullable=False, index=True)
    senha = Column("senha", String(255), nullable=False)
    permissoes = Column("permissoes", String(20), nullable=False, default="usuario")

    # Sinônimos de compatibilidade com os retornos e campos do server.py original
    Nome = synonym("nome")
    Email = synonym("email")
    Senha = synonym("senha")
    Permissoes = synonym("permissoes")

    libraries = relationship("Library", back_populates="usuario", cascade="all, delete-orphan")

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Converte a instância para dicionário público ou completo."""
        data = {
            "id": self.id,
            "Nome": self.nome,
            "Email": self.email,
            "Permissoes": self.permissoes,
        }
        if include_sensitive:
            data["Senha"] = self.senha
        return data

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, permissoes={self.permissoes})>"


class Library(Base):
    """
    Modelo ORM que mapeia a tabela 'library' no PostgreSQL.
    Representa as estantes/bibliotecas virtuais dos usuários.
    """
    __tablename__ = "library"

    id = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    nome = Column(String(255), nullable=False)

    usuario = relationship("User", back_populates="libraries")
    links = relationship("LinkLibrary", back_populates="biblioteca", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Library(id={self.id}, nome={self.nome}, id_usuario={self.id_usuario})>"


class LinkLibrary(Base):
    """
    Modelo ORM que mapeia a tabela associativa 'link_library' no PostgreSQL.
    Conecta livros (editions) às bibliotecas virtuais dos usuários.
    """
    __tablename__ = "link_library"

    id = Column(Integer, primary_key=True, index=True)
    id_biblioteca = Column(Integer, ForeignKey("library.id", ondelete="CASCADE"), nullable=False)
    id_livro = Column(Integer, ForeignKey("editions.id", ondelete="CASCADE"), nullable=False)

    biblioteca = relationship("Library", back_populates="links")
    livro = relationship("Edition", back_populates="links")

    def __repr__(self) -> str:
        return f"<LinkLibrary(id={self.id}, id_biblioteca={self.id_biblioteca}, id_livro={self.id_livro})>"
