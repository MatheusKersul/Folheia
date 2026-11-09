"""
Funções de acesso e manipulação de dados (CRUD) implementadas com SQLAlchemy ORM.
"""
from crud.crud_user import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    list_users,
)
from crud.crud_book import (
    edicao_visivel_para,
    find_book,
    get_book_by_author,
    get_book_by_isbn,
    get_book_by_title,
    get_edition_by_id,
    get_edition_visible_to,
    get_verified_edition_by_isbn,
)
from crud.crud_library import (
    add_link,
    create_custom_edition_and_link,
    delete_link,
    get_item_for_user,
    get_library_by_user,
    get_link,
    get_or_create_library,
    list_custom_editions,
    list_items,
)

__all__ = [
    "create_user",
    "get_user_by_email",
    "get_user_by_id",
    "list_users",
    "get_book_by_isbn",
    "get_book_by_title",
    "get_book_by_author",
    "find_book",
    "get_edition_by_id",
    "get_verified_edition_by_isbn",
    "edicao_visivel_para",
    "get_edition_visible_to",
    "add_link",
    "create_custom_edition_and_link",
    "delete_link",
    "get_item_for_user",
    "get_library_by_user",
    "get_link",
    "get_or_create_library",
    "list_custom_editions",
    "list_items",
]
