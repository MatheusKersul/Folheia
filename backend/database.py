"""
Módulo de Banco de Dados (PostgreSQL / RDS via SQLAlchemy).
Centraliza o engine, SessionLocal, Base declarativa e a dependência get_db.
"""
from core.database import engine, SessionLocal, Base, get_db

__all__ = ["engine", "SessionLocal", "Base", "get_db"]
