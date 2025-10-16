"""
Database connection usando SQLAlchemy 2.0
Patrón: Dependency Injection para sessions
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from typing import Generator
from app.core.config import get_settings

settings = get_settings()

# Engine: Pool de conexiones a PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Verifica conexión antes de usar
    pool_size=10,  # Max 10 conexiones simultáneas
    max_overflow=20,  # Hasta 20 adicionales si es necesario
    echo=settings.DEBUG,  # Log SQL queries si DEBUG=True
)

# SessionLocal: Factory para crear sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# Base para todos los models
class Base(DeclarativeBase):
    """
    Base class para todos los models SQLAlchemy

    Uso:
        class Order(Base):
            __tablename__ = "orders"
            ...
    """
    pass


def get_db() -> Generator[Session, None, None]:
    """
    Dependency para FastAPI

    Uso:
        @app.get("/orders")
        def get_orders(db: Session = Depends(get_db)):
            ...

    Cierra automáticamente la sesión al terminar
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
