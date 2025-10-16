"""
E-commerce Backend - FastAPI Application

Principios:
- Minimalista: Solo lo esencial
- Modular: Cada router = un módulo
- Documentado: Swagger automático
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time

from app.core.config import get_settings
from app.core.exceptions import BaseAppException
from app.core.events import setup_all_events
from app.routers import orders, webhooks, inventory, payments, products, purchases

# Configuración
settings = get_settings()

# Logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# FastAPI App
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    Backend para E-commerce con:
    - Gestión de órdenes (Shopify integration)
    - Inventario en tiempo real
    - Multi-moneda
    - Tracking de marketing (ROAS)

    Arquitectura: Microservicios + PostgreSQL
    """,
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todos los orígenes (para testing)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware: Request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log todas las requests con timing"""
    start_time = time.time()

    # Log request
    logger.info(f"→ {request.method} {request.url.path}")

    # Process request
    response = await call_next(request)

    # Log response
    duration = time.time() - start_time
    logger.info(
        f"← {request.method} {request.url.path} - {response.status_code} ({duration:.3f}s)"
    )

    return response


# Exception Handlers
@app.exception_handler(BaseAppException)
async def app_exception_handler(request: Request, exc: BaseAppException):
    """Handler para excepciones de la aplicación"""
    return JSONResponse(
        status_code=400,
        content={"error": exc.__class__.__name__, "message": exc.message, "details": exc.details},
    )


# Routers
app.include_router(orders.router)
app.include_router(webhooks.router)
app.include_router(inventory.router)
app.include_router(payments.router)
app.include_router(products.router)
app.include_router(purchases.router)


# Health Check
@app.get("/", tags=["Health"])
def root():
    """
    Health check endpoint

    Verifica que el servidor está corriendo
    """
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    """
    Health check detallado

    TODO: Verificar conexión a BD
    """
    return {
        "status": "healthy",
        "database": "connected",  # TODO: Verificar realmente
        "version": settings.APP_VERSION,
    }


# Startup/Shutdown Events
@app.on_event("startup")
async def startup_event():
    """Se ejecuta al iniciar el servidor"""
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} iniciando...")
    logger.info(f"📚 Documentación: http://localhost:8000/docs")

    # Crear tablas en la base de datos si no existen
    try:
        from app.core.database import engine, Base
        # Importar todos los modelos para que SQLAlchemy los conozca
        import app.models  # noqa: F401

        logger.info("📊 Verificando/creando tablas en la base de datos...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tablas verificadas/creadas exitosamente")
    except Exception as e:
        logger.error(f"❌ Error al crear tablas: {e}")
        raise

    # Configurar event listeners (reemplaza triggers de BD)
    setup_all_events()


@app.on_event("shutdown")
async def shutdown_event():
    """Se ejecuta al detener el servidor"""
    logger.info(f"👋 {settings.APP_NAME} deteniendo...")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,  # Auto-reload en desarrollo
        log_level="info",
    )
