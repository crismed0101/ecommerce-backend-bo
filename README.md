# E-commerce Backend - Bolivia

Backend moderno para e-commerce con FastAPI, PostgreSQL y arquitectura de servicios.

## Características

- **REST API completa** con 23 endpoints
- **Multi-moneda** (BOB, USD)
- **Gestión de inventario** en 9 departamentos de Bolivia
- **Tracking de marketing** (UTM parameters, ROAS)
- **Integración con Shopify** via webhooks
- **Arquitectura de servicios** (no triggers SQL)
- **Documentación automática** (Swagger UI + ReDoc)

## Stack Tecnológico

- **Framework:** FastAPI 0.104+
- **ORM:** SQLAlchemy 2.0
- **Base de datos:** PostgreSQL 17
- **Validación:** Pydantic
- **Migraciones:** Alembic (próximamente)

## Arquitectura

```
backend/
├── app/
│   ├── core/           # Configuración, database, eventos
│   ├── models/         # Modelos SQLAlchemy (auto-generados)
│   ├── schemas/        # Pydantic schemas (validación)
│   ├── services/       # Lógica de negocio
│   ├── routers/        # Endpoints REST
│   ├── adapters/       # Integraciones externas (Shopify, etc.)
│   └── main.py         # Aplicación principal
├── .env                # Variables de entorno (NO commitear)
├── .env.example        # Template de variables
└── requirements.txt    # Dependencias
```

## Schemas PostgreSQL

El proyecto utiliza una base de datos multi-schema:

- `operations` - Órdenes, clientes, carriers, tracking
- `product` - Productos, variantes, inventario, compras
- `finance` - Cuentas, transacciones
- `marketing` - Campañas, ads, métricas

## Endpoints Principales

### Orders (4 endpoints)
- `POST /api/v1/orders` - Crear orden completa
- `GET /api/v1/orders` - Listar con filtros y paginación
- `GET /api/v1/orders/{order_id}` - Obtener detalle
- `PATCH /api/v1/orders/{order_id}/status` - Actualizar estado

### Inventory (5 endpoints)
- `POST /api/v1/inventory/transfer` - Transferir stock entre departamentos
- `GET /api/v1/inventory/alerts/low-stock` - Alertas de stock bajo
- `POST /api/v1/inventory/adjustment` - Ajustes con auditoría
- `GET /api/v1/inventory/turnover/{variant_id}` - Rotación de inventario
- `GET /api/v1/inventory/valuation/{variant_id}` - Valuación FIFO/LIFO

### Payments (3 endpoints)
- `POST /api/v1/payments/batch-paid` - Procesar pagos en lote
- `GET /api/v1/payments/alerts/negative-balance` - Alertas de carriers
- `GET /api/v1/payments/balance-trend/{carrier_id}` - Tendencias

### Products (5 endpoints)
- `PATCH /api/v1/products/variants/{variant_id}/price` - Actualizar precio
- `GET /api/v1/products/alerts/price-changes` - Alertas de precios
- `GET /api/v1/products/{product_id}/related` - Productos relacionados
- `POST /api/v1/products/{product_id}/related` - Agregar relacionado
- `GET /api/v1/products/{product_id}/recommendations` - Upsell/Cross-sell

### Purchases (2 endpoints)
- `POST /api/v1/purchases/validate-price` - Validar precio de compra
- `GET /api/v1/purchases/price-history/{variant_id}` - Historial

### Webhooks (2 endpoints)
- `POST /webhooks/shopify/orders/create` - Recibir órdenes de Shopify
- `GET /webhooks/health` - Health check

## Instalación

### 1. Clonar repositorio

```bash
git clone https://github.com/tu-usuario/ecommerce-backend.git
cd ecommerce-backend
```

### 2. Crear entorno virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus credenciales
```

### 5. Iniciar servidor

```bash
# Desarrollo (auto-reload)
uvicorn app.main:app --reload

# Producción
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Documentación API

Una vez iniciado el servidor, acceder a:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

## Deployment con Docker

```bash
# Próximamente
docker-compose up -d
```

## Testing

```bash
# Próximamente
pytest
```

## Servicios Implementados

- `OrderService` - Gestión completa de órdenes
- `InventoryService` - Control de stock multi-departamento
- `ProductService` - Catálogo y pricing
- `PaymentService` - Pagos a carriers
- `PurchaseService` - Compras a proveedores
- `IDGenerator` - IDs únicos secuenciales

## Validaciones Críticas

- **Stock insuficiente** - Previene órdenes sin inventario
- **Duplicados 24h** - Detecta órdenes duplicadas
- **Totales de orden** - Valida que subtotal items = total orden
- **Precios de compra** - Alerta cambios > 100%
- **Balances negativos** - Detecta carriers con deuda excesiva

## Contribuir

1. Fork el proyecto
2. Crear feature branch (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -m 'Agregar nueva funcionalidad'`)
4. Push al branch (`git push origin feature/nueva-funcionalidad`)
5. Abrir Pull Request

## Licencia

Privado - Todos los derechos reservados

## Autor

**Tu Nombre** - E-commerce Bolivia

---

**Documentación completa:** Ver `/docs` endpoint
**Swagger UI:** http://localhost:8000/docs
