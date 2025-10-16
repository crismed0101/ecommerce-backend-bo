# ANALISIS EXHAUSTIVO PRE-PRODUCCION
## Backend E-commerce BO - FastAPI + PostgreSQL

**Fecha:** 2025-10-15
**Estado actual:** FUNCIONAL BASICO - Necesita mejoras antes de producción

---

## 1. INVENTARIO ACTUAL DEL BACKEND

### ✅ COMPLETADO Y FUNCIONANDO

#### Servicios Implementados:
- **IDGenerator** (`app/services/id_generator.py`)
  - ✅ Genera IDs para: orders, customers, order_items, products, variants, inventory
  - ✅ Formato consistente con la BD

- **OrderService** (`app/services/order_service.py`)
  - ✅ create_full_order() - Crea orden completa (customer + order + items + tracking)
  - ✅ update_status() - Cambia estado de orden
  - ✅ _handle_delivered_order() - Reduce inventario al entregar
  - ✅ _handle_returned_order() - Aumenta inventario al devolver
  - ✅ _find_or_create_customer() - Busca por phone o crea nuevo
  - ✅ _update_customer_stats() - Actualiza total_orders y total_spent_bob
  - ⚠️  FALTA: Validación de stock ANTES de confirmar orden

- **ProductService** (`app/services/product_service.py`)
  - ✅ find_or_create_variant() - Búsqueda en cascada (shopify_variant_id → sku → name)
  - ✅ _create_product_and_variant() - Auto-crea producto + variante + inventario
  - ✅ _find_or_create_product() - Busca o crea producto padre
  - ✅ _generate_sku() - Genera SKU automático (ej: CHOMPAROJA-001)
  - ✅ _create_initial_inventory() - Crea inventario en los 9 departamentos (stock=0)
  - ✅ IDEMPOTENCIA: Verifica inventarios existentes antes de crear

- **InventoryService** (`app/services/inventory_service.py`)
  - ✅ create_movement() - Crea movimiento idempotente (verifica reference_id)
  - ✅ _update_stock() - Actualiza stock con SELECT FOR UPDATE (pessimistic locking)
  - ✅ reduce_stock_on_delivery() - Reduce stock al entregar (idempotente)
  - ✅ increase_stock_on_return() - Aumenta stock al devolver (idempotente)
  - ✅ increase_stock_on_purchase() - Aumenta stock al comprar (idempotente)
  - ✅ validate_stock() - Verifica si hay stock suficiente
  - ✅ get_stock() - Obtiene stock actual
  - ⚠️  FALTA: Validación PREVIA antes de permitir cambio de estado a "delivered"

#### Routers/Endpoints:
- **OrdersRouter** (`app/routers/orders.py`)
  - ✅ POST /api/v1/orders - Crear orden completa (FUNCIONAL)
  - ✅ PATCH /api/v1/orders/{order_id}/status - Actualizar estado (FUNCIONAL)
  - ❌ GET /api/v1/orders/{order_id} - Obtener orden (NOT IMPLEMENTED)
  - ❌ GET /api/v1/orders - Listar órdenes (NO EXISTE)

#### Schemas Pydantic:
- **OrderSchemas** (`app/schemas/order.py`)
  - ✅ OrderCreate - Validación completa de input
  - ✅ CustomerCreate - Validación de customer
  - ✅ OrderItemCreate - Validación de items
  - ✅ OrderStatusUpdate - Validación de cambio de estado
  - ✅ OrderCreateResponse - Respuesta estructurada
  - ✅ Enums: DepartmentEnum, PaymentMethodEnum, OrderStatusEnum

#### Modelos SQLAlchemy:
- ✅ **operations_generated.py** - 100% sincronizado con BD
- ✅ **product_generated.py** - 100% sincronizado con BD
- ✅ **finance_generated.py** - 100% sincronizado con BD
- ✅ **marketing_generated.py** - 100% sincronizado con BD
- ✅ Relaciones corregidas (OrderTracking es 1-to-1 con Orders, no herencia)

#### Core:
- ✅ database.py - Conexión a PostgreSQL con pooling
- ✅ config.py - Configuración con variables de entorno
- ✅ exceptions.py - Excepciones personalizadas
- ✅ main.py - App FastAPI con CORS, logging, health checks

---

## 2. TRIGGERS/FUNCIONES POSTGRESQL - ESTADO DE MIGRACION

### Total en BD: 87 triggers + 68 funciones

### 🔴 CRITICAS PENDIENTES (ALTA PRIORIDAD)

#### operations Schema:

1. **trg_02_validate_stock_on_delivery** (BEFORE UPDATE on order_tracking)
   - ❌ NO MIGRADO
   - **Qué hace:** Valida que haya stock suficiente ANTES de cambiar estado a "delivered"
   - **Por qué es crítico:** Evita reducir inventario negativo
   - **Función:** `product.fn_validate_sufficient_stock()`
   - **Migración:** Debe agregarse a `OrderService.update_status()` ANTES de llamar `_handle_delivered_order()`

2. **trg_11_calculate_delivery_costs** (AFTER UPDATE on order_tracking)
   - ❌ NO MIGRADO
   - **Qué hace:** Calcula costos de entrega/devolución según carrier y departamento
   - **Función:** `operations.fn_calculate_delivery_return_costs()`
   - **Migración:** Crear `DeliveryCostService`

3. **trg_11_update_payment** (AFTER UPDATE on order_tracking)
   - ❌ NO MIGRADO
   - **Qué hace:** Actualiza pagos cuando cambia estado de orden
   - **Función:** `operations.fn_update_payment_from_order()`
   - **Migración:** Crear `PaymentService` o agregar a `OrderService`

4. **trg_01_validate_customer** (BEFORE INSERT on orders)
   - ⚠️  PARCIALMENTE MIGRADO
   - **Qué hace:** Valida que customer esté activo
   - **Función:** `operations.fn_validate_customer_active()`
   - **Estado actual:** Backend valida existencia pero NO valida `is_active`
   - **Migración:** Agregar validación de `is_active` en `_find_or_create_customer()`

#### product Schema:

5. **trg_validate_movement** (BEFORE INSERT/UPDATE on inventory_movements)
   - ❌ NO MIGRADO
   - **Qué hace:** Valida que movimientos de inventario sean consistentes
   - **Función:** `product.fn_validate_movement_before_insert()`
   - **Migración:** Agregar a `InventoryService.create_movement()`

6. **trg_recalculate_inventory** (AFTER INSERT/UPDATE/DELETE on inventory_movements)
   - ⚠️  PARCIALMENTE MIGRADO
   - **Qué hace:** Recalcula stock en `inventory` cuando cambian movimientos
   - **Función:** `product.fn_recalculate_inventory_stock()`
   - **Estado actual:** `_update_stock()` hace esto pero sin validaciones extra
   - **Migración:** Verificar que lógica sea idéntica

### ✅ YA MIGRADOS

1. **trg_00_orders_generate_id** → `IDGenerator.generate_order_id()`
2. **trg_00_customers_generate_id** → `IDGenerator.generate_customer_id()`
3. **trg_00_order_items_generate_id** → `IDGenerator.generate_order_item_id()`
4. **trg_00_products_generate_id** → `IDGenerator.generate_product_id()`
5. **trg_00_variants_generate_id** → `IDGenerator.generate_variant_id()`
6. **trg_00_inventory_generate_id** → `IDGenerator.generate_inventory_id()`
7. **trg_10_auto_create_order_tracking** → `OrderService.create_full_order()` con idempotencia
8. **trg_10_update_customer_stats** → `OrderService._update_customer_stats()`
9. **trg_12_manage_inventory** → `OrderService._handle_delivered_order()` + `InventoryService`
10. **trg_02_create_inventory** → `ProductService._create_initial_inventory()`

### 📋 TRIGGERS NO CRITICOS PARA ORDERS (Migrar después)

- `trg_00_*_update_timestamp` → Podrían mantenerse en BD o migrar después
- Finance triggers (68 funciones) → No son críticos para Orders
- Marketing triggers → No son críticos para Orders
- Purchase triggers → No son críticos para Orders inicialmente

---

## 3. PROBLEMAS CRITICOS DETECTADOS

### 🔴 PROBLEMA 1: No hay validación de stock antes de entregar orden

**Escenario:**
- Orden con 10 unidades del producto X
- Inventario actual: 0 unidades en LA PAZ
- Usuario cambia estado a "delivered"
- Backend reduce inventario: 0 - 10 = -10 ❌

**Solución:**
```python
# En OrderService.update_status() ANTES de _handle_delivered_order()
if new_status == OrderStatusEnum.DELIVERED:
    # VALIDAR STOCK PRIMERO
    for item in order.order_items:
        has_stock = InventoryService.validate_stock(
            db=db,
            variant_id=item.product_variant_id,
            department=order.customer.department,
            quantity_required=item.quantity
        )
        if not has_stock:
            raise InsufficientStockException(
                f"Stock insuficiente para {item.product_name}",
                details={
                    "variant_id": item.product_variant_id,
                    "department": order.customer.department,
                    "required": item.quantity
                }
            )

    # AHORA SÍ reducir inventario
    self._handle_delivered_order(db, order)
```

### 🔴 PROBLEMA 2: InventoryService permite stock negativo

**Código actual:**
```python
# inventory_service.py línea 138
inventory.stock_quantity += quantity_change
```

Si `quantity_change = -10` y `stock_quantity = 0`, resultado = `-10` ❌

**Solución:**
```python
# En _update_stock() AGREGAR VALIDACION:
if quantity_change < 0:  # Es una salida
    if inventory.stock_quantity + quantity_change < 0:
        raise InsufficientStockException(
            f"Stock insuficiente. Disponible: {inventory.stock_quantity}, Requerido: {abs(quantity_change)}"
        )

inventory.stock_quantity += quantity_change
```

### 🔴 PROBLEMA 3: Falta endpoint GET /orders/{order_id}

**Estado actual:** `raise HTTPException(status_code=501, detail="Not implemented")`

**Impacto:** No puedes consultar una orden después de crearla (necesario para debugging y N8N workflows)

**Solución:** Implementar query con JOINs completos

### ⚠️  PROBLEMA 4: Customer `is_active` no se valida

**Estado actual:** Backend crea/actualiza customers sin verificar `is_active`

**Solución:**
```python
# En _find_or_create_customer() AGREGAR:
if customer and not customer.is_active:
    raise CustomerInactiveException(f"Cliente {customer.customer_id} está inactivo")
```

### ⚠️  PROBLEMA 5: No hay validación de carrier activo

**Estado actual:** Orders se crean con `carrier_id` sin validar si carrier está activo

**Solución:** Validar en `create_full_order()` si `carrier_id` es proporcionado

---

## 4. MEJORAS RECOMENDADAS ANTES DE PRODUCCION

### Alta Prioridad:

1. **✅ Implementar validación de stock ANTES de cambiar estado a "delivered"**
2. **✅ Prevenir stock negativo en InventoryService._update_stock()**
3. **✅ Implementar GET /orders/{order_id}** (para debugging y N8N)
4. **✅ Validar customer.is_active** en _find_or_create_customer()
5. **✅ Implementar tests unitarios** para servicios críticos

### Media Prioridad:

6. **Migrar fn_calculate_delivery_costs** (crear DeliveryCostService)
7. **Migrar fn_update_payment_from_order** (crear PaymentService)
8. **Implementar GET /orders** (listar órdenes con filtros)
9. **Implementar GET /products** (listar productos)
10. **Implementar GET /inventory** (consultar inventario)
11. **Health check real de BD** (actualmente solo retorna "connected")

### Baja Prioridad (Post-lanzamiento):

12. Migrar triggers de timestamp a backend
13. Migrar triggers de finance
14. Migrar triggers de marketing
15. Implementar autenticación JWT
16. Implementar rate limiting
17. Implementar caching con Redis

---

## 5. PLAN DE MIGRACION PROGRESIVA

### FASE 1: CRÍTICO (HOY - Antes de producción)

- [ ] Implementar validación de stock antes de delivery
- [ ] Prevenir stock negativo
- [ ] Validar customer.is_active
- [ ] Implementar GET /orders/{order_id}
- [ ] Tests básicos

### FASE 2: IMPORTANTE (Semana 1)

- [ ] Migrar fn_calculate_delivery_costs
- [ ] Migrar fn_update_payment_from_order
- [ ] Implementar GET /orders con filtros
- [ ] Implementar logging robusto
- [ ] Desactivar triggers migrados en BD

### FASE 3: MEJORAS (Semana 2-3)

- [ ] Migrar validaciones de movements
- [ ] Implementar endpoints de productos
- [ ] Implementar endpoints de inventory
- [ ] Tests de integración completos
- [ ] Documentación completa

### FASE 4: OPTIMIZACIÓN (Mes 1+)

- [ ] Migrar triggers de finance
- [ ] Migrar triggers de marketing
- [ ] Implementar autenticación
- [ ] Implementar caching
- [ ] Monitoring con Sentry/DataDog

---

## 6. CHECKLIST PRE-PRODUCCION

### Backend:
- [x] Servicios core implementados
- [x] Modelos sincronizados con BD
- [x] Endpoints básicos funcionando
- [ ] Validación de stock implementada
- [ ] Stock negativo prevenido
- [ ] Endpoint GET orders implementado
- [ ] Validación de customer.is_active
- [ ] Tests unitarios mínimos
- [ ] Logging configurado correctamente
- [ ] Variables de entorno para producción

### Database:
- [x] Esquemas creados
- [x] Triggers activos (temporalmente OK)
- [ ] Plan para desactivar triggers migrados
- [ ] Backup strategy definida
- [ ] Monitoring configurado

### Deploy:
- [ ] Backend desplegado en Hetzner
- [ ] PostgreSQL accesible desde Hetzner
- [ ] Nginx/reverse proxy configurado
- [ ] SSL/HTTPS configurado
- [ ] Variables de entorno en producción
- [ ] Logs configurados
- [ ] Health checks monitoreados

---

## 7. ARQUITECTURA ACTUAL vs OBJETIVO

### ACTUAL:
```
N8N (Hetzner) → ngrok tunnel → Backend (local) → PostgreSQL (local)
                                   ↓
                            Triggers en BD activos
```

### OBJETIVO INMEDIATO:
```
N8N (Hetzner) → Backend (Hetzner) → PostgreSQL (Hetzner o local VPN)
                    ↓
             Backend maneja TODO
             Triggers críticos DISABLED
```

### OBJETIVO FINAL:
```
N8N → Backend (Hetzner) → PostgreSQL (Hetzner)
         ↓
    100% lógica en backend
    TODOS los triggers desactivados
    BD solo almacena datos
```

---

## 8. RESUMEN EJECUTIVO

### ✅ LO QUE FUNCIONA:
- Creación completa de órdenes desde N8N
- Auto-creación de customers, products, variants
- Actualización de customer stats
- Reducción/aumento de inventario en delivery/return
- Idempotencia básica

### ❌ FALTA ANTES DE PRODUCCIÓN:
1. **CRÍTICO:** Validación de stock antes de delivery
2. **CRÍTICO:** Prevenir stock negativo
3. **IMPORTANTE:** Endpoint GET orders
4. **IMPORTANTE:** Validación customer.is_active
5. **IMPORTANTE:** Deployment en Hetzner

### 📊 ESTADÍSTICAS:
- Triggers en BD: 87 total, 10 ya migrados (11.5%)
- Funciones en BD: 68 total, ~6 ya migradas (8.8%)
- Servicios backend: 4 (IDGenerator, Order, Product, Inventory)
- Endpoints: 2 funcionales (POST orders, PATCH status)
- Schemas: 8 (completos y validados)

### 🎯 PRÓXIMO PASO:
**IMPLEMENTAR LAS 4 MEJORAS CRÍTICAS LISTADAS ARRIBA**

---

**Conclusión:** El backend está en estado FUNCIONAL BÁSICO pero necesita **validaciones críticas** antes de producción. Especialmente la validación de stock para evitar inventario negativo. Todo lo demás puede migrarse progresivamente.
