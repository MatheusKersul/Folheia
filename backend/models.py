"""
Modelos ORM do SQLAlchemy que espelham as tabelas do PostgreSQL.
Mapeamento de:
- User (tabela 'users')
- Edition (tabela 'editions')
- Library (tabela 'library')
- LinkLibrary (tabela 'link_library')
"""
from core.database import Base
from models.user import User, Library, LinkLibrary
from models.book import Edition

__all__ = ["Base", "User", "Library", "LinkLibrary", "Edition"]
