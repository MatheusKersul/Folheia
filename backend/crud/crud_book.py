from typing import Optional

from sqlalchemy.orm import Query, Session

from models.book import Edition


def _filtrar_oficiais(query: Query, apenas_verificadas: bool) -> Query:
    """
    Restringe a consulta ao catálogo oficial.

    Edições próprias (``verificada=False``) nunca entram nas buscas públicas:
    elas são privadas do usuário que as criou.
    """
    if apenas_verificadas:
        return query.filter(Edition.verificada.is_(True))
    return query


def get_book_by_isbn(
    db: Session, isbn: str, apenas_verificadas: bool = True
) -> Optional[Edition]:
    """
    Busca um livro pelo ISBN-13 (removendo hifens e espaços) utilizando SQLAlchemy ORM.
    """
    clean_isbn = isbn.replace("-", "").strip()
    query = db.query(Edition).filter(Edition.isbn_13 == clean_isbn)
    return _filtrar_oficiais(query, apenas_verificadas).first()


def get_book_by_title(
    db: Session, title: str, apenas_verificadas: bool = True
) -> Optional[Edition]:
    """
    Busca o primeiro livro correspondente ao título (case-insensitive com ILIKE).
    """
    termo_limpo = title.strip()
    query = db.query(Edition).filter(Edition.titulo.ilike(f"%{termo_limpo}%"))
    return _filtrar_oficiais(query, apenas_verificadas).first()


def get_book_by_author(
    db: Session, author: str, apenas_verificadas: bool = True
) -> Optional[Edition]:
    """
    Busca o primeiro livro correspondente ao autor (case-insensitive com ILIKE).
    """
    termo_limpo = author.strip()
    query = db.query(Edition).filter(Edition.autor.ilike(f"%{termo_limpo}%"))
    return _filtrar_oficiais(query, apenas_verificadas).first()


def find_book(
    db: Session, tipo: str, termo: str, apenas_verificadas: bool = True
) -> Optional[Edition]:
    """
    Despacha a busca do livro com base no critério: 'isbn', 'titulo' ou 'autor'.
    Lança ValueError se o tipo de busca for inválido.
    """
    tipo_normalizado = (tipo or "").strip().lower()
    if tipo_normalizado == "isbn":
        return get_book_by_isbn(db, termo, apenas_verificadas=apenas_verificadas)
    elif tipo_normalizado == "titulo":
        return get_book_by_title(db, termo, apenas_verificadas=apenas_verificadas)
    elif tipo_normalizado == "autor":
        return get_book_by_author(db, termo, apenas_verificadas=apenas_verificadas)
    else:
        raise ValueError(f"Tipo de busca inválido: '{tipo}'. Tipos válidos: 'isbn', 'titulo', 'autor'.")


def get_edition_by_id(db: Session, edition_id: int) -> Optional[Edition]:
    """Busca uma edição pelo seu identificador primário, sem filtro de visibilidade."""
    return db.query(Edition).filter(Edition.id == edition_id).first()


def get_verified_edition_by_isbn(db: Session, isbn: str) -> Optional[Edition]:
    """
    Busca uma edição OFICIAL pelo ISBN.

    Usado para impedir que uma edição própria repita o ISBN de uma obra já
    existente no catálogo.
    """
    clean_isbn = (isbn or "").replace("-", "").strip()
    if not clean_isbn:
        return None
    return (
        db.query(Edition)
        .filter(Edition.isbn_13 == clean_isbn, Edition.verificada.is_(True))
        .first()
    )


def edicao_visivel_para(edition: Edition, usuario_id: int) -> bool:
    """
    Regra única de visibilidade de uma edição.

    - Catálogo oficial (``verificada=True``): visível para todos.
    - Edição própria (``verificada=False``): visível apenas ao criador.
    """
    if edition is None:
        return False
    if bool(edition.verificada):
        return True
    return edition.id_usuario_criador is not None and edition.id_usuario_criador == usuario_id


def get_edition_visible_to(
    db: Session, edition_id: int, usuario_id: int
) -> Optional[Edition]:
    """
    Retorna a edição apenas se ela for visível para o usuário informado.

    Caso contrário retorna ``None`` — o chamador deve responder 404 para não
    revelar a existência de edições privadas de terceiros.
    """
    edition = get_edition_by_id(db, edition_id)
    if edition is None or not edicao_visivel_para(edition, usuario_id):
        return None
    return edition


def salvar_ou_atualizar_edicao_scraped(
    db: Session, dados: dict, s3_images_url: Optional[str] = None
) -> Edition:
    """
    Salva uma nova edição oficial proveniente de scraping no RDS ou atualiza
    uma existente se o ISBN-13 já estiver cadastrado.
    """
    isbn_bruto = dados.get("isbn_13") or dados.get("isbn") or ""
    clean_isbn = isbn_bruto.replace("-", "").strip()

    edition = None
    if clean_isbn:
        edition = get_verified_edition_by_isbn(db, clean_isbn)

    final_image_url = s3_images_url or dados.get("images_url")

    if edition:
        if final_image_url and (not edition.images_url or "s3" in final_image_url):
            edition.images_url = final_image_url

        if not edition.editora and dados.get("editora"):
            edition.editora = dados.get("editora")
        if not edition.data_publicacao and dados.get("data_publicacao"):
            edition.data_publicacao = str(dados.get("data_publicacao"))
        if not edition.formato and dados.get("formato"):
            edition.formato = dados.get("formato")
        if not edition.num_paginas and dados.get("num_paginas"):
            try:
                edition.num_paginas = int(dados.get("num_paginas"))
            except (ValueError, TypeError):
                pass
        if not edition.autor and dados.get("autor"):
            edition.autor = dados.get("autor")
        if not edition.titulo and dados.get("titulo"):
            edition.titulo = dados.get("titulo")

        db.commit()
        db.refresh(edition)
        return edition

    num_paginas = None
    if dados.get("num_paginas"):
        try:
            num_paginas = int(dados.get("num_paginas"))
        except (ValueError, TypeError):
            num_paginas = None

    nova_edicao = Edition(
        isbn_13=clean_isbn if clean_isbn else None,
        titulo=dados.get("titulo"),
        autor=dados.get("autor"),
        editora=dados.get("editora"),
        data_publicacao=str(dados.get("data_publicacao")) if dados.get("data_publicacao") else None,
        formato=dados.get("formato"),
        num_paginas=num_paginas,
        images_url=final_image_url,
        verificada=True,
        id_usuario_criador=None,
    )

    db.add(nova_edicao)
    db.commit()
    db.refresh(nova_edicao)
    return nova_edicao

