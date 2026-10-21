from typing import Optional
from sqlalchemy.orm import Session
from models.book import Edition

def get_book_by_isbn(db: Session, isbn: str) -> Optional[Edition]:
    """
    Busca um livro pelo ISBN-13 (removendo hifens e espaços) utilizando SQLAlchemy ORM.
    """
    clean_isbn = isbn.replace("-", "").strip()
    return db.query(Edition).filter(Edition.isbn_13 == clean_isbn).first()

def get_book_by_title(db: Session, title: str) -> Optional[Edition]:
    """
    Busca o primeiro livro correspondente ao título (case-insensitive com ILIKE).
    """
    termo_limpo = title.strip()
    return db.query(Edition).filter(Edition.titulo.ilike(f"%{termo_limpo}%")).first()

def get_book_by_author(db: Session, author: str) -> Optional[Edition]:
    """
    Busca o primeiro livro correspondente ao autor (case-insensitive com ILIKE).
    """
    termo_limpo = author.strip()
    return db.query(Edition).filter(Edition.autor.ilike(f"%{termo_limpo}%")).first()

def find_book(db: Session, tipo: str, termo: str) -> Optional[Edition]:
    """
    Despacha a busca do livro com base no critério: 'isbn', 'titulo' ou 'autor'.
    Lança ValueError se o tipo de busca for inválido.
    """
    tipo_normalizado = (tipo or "").strip().lower()
    if tipo_normalizado == "isbn":
        return get_book_by_isbn(db, termo)
    elif tipo_normalizado == "titulo":
        return get_book_by_title(db, termo)
    elif tipo_normalizado == "autor":
        return get_book_by_author(db, termo)
    else:
        raise ValueError(f"Tipo de busca inválido: '{tipo}'. Tipos válidos: 'isbn', 'titulo', 'autor'.")
