from routers.auth import router as auth_router
from routers.books import router as books_router
from routers.library import router as library_router
from routers.system import router as system_router
from routers.scrap import router as scrap_router
from routers.admin import router as admin_router

__all__ = ["auth_router", "books_router", "library_router", "system_router", "scrap_router", "admin_router"]
