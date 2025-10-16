"""
Configuración centralizada usando Pydantic Settings
Carga variables de entorno desde .env
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Settings del proyecto

    Todas las variables de entorno se cargan automáticamente
    desde el archivo .env
    """

    # App
    APP_NAME: str = "E-commerce Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql://ecommerce_user:password@178.156.173.101:5432/dbprod"

    # Security
    SECRET_KEY: str = "tu-secret-key-super-segura-cambiala-en-produccion"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS
    ALLOWED_ORIGINS: str = "*"

    # Shopify
    SHOPIFY_WEBHOOK_SECRET: str = ""

    # Meta Ads
    META_ACCESS_TOKEN: str = ""
    META_AD_ACCOUNT_ID: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Singleton pattern: Solo carga settings una vez
    """
    return Settings()
