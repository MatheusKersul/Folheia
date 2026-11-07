from routers.auth import router as auth_router
from routers.books import router as books_router
from routers.system import router as system_router
from routers.scrap import router as scrap_router

__all__ = ["auth_router", "books_router", "system_router", "scrap_router"]
