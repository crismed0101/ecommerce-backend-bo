# PLAN DE MIGRACIÓN COMPLETA DE TRIGGERS

**Fecha:** 2025-10-15
**Estado:** EN PROGRESO
**Total Triggers:** 87
**Migrados:** 35+ (40%+)
**Pendientes:** 52 (60%)

---

## RESUMEN DE MIGRACIÓN

### ✅ FASE 1-3: COMPLETADAS (18 triggers migrados)
- Sistema de órdenes 100% funcional
- Validaciones críticas implementadas
- Gestión de inventario completa
- Costos y pagos migrados

### ✅ FASE 4: COMPLETADA (17 triggers migrados)
- **Timestamps automáticos**: Event listeners en `app/core/events.py`
- Reemplaza TODOS los triggers `fn_update_timestamp` (~17 triggers)
- Se aplica automáticamente a todos los modelos con `updated_at`

### ⏳ FASE 5-8: EN PROGRESO

---

## ANÁLISIS DE TRIGGERS PENDIENTES

### OPERATIONS (7 triggers pendientes)
**Prioridad: BAJA** (ya se manejan desde el backend en los servicios)

1. **trg_01_validate_customer** - Ya implementado en OrderService.app/services/order_service.py:389
2. **trg_validate_payment_carrier_active** - Implementado en PaymentService
3. Resto son triggers de timestamp o generación de IDs → Ya migrados

**Acción:** Mantener en BD (redundancia) o desactivar

---

### PRODUCT (20 triggers pendientes)
**Prioridad: ALTA** (funcionalidad avanzada de compras e inventario)

#### CRÍTICOS para compras:
4. **trg_sync_purchase_to_inventory** (3 triggers: INSERT/UPDATE/DELETE)
   - Sincroniza compras → movimientos de inventario
   - **MIGRAR A:** `PurchaseService.sync_to_inventory()`

5. **trg_recalculate_purchase_totals** (3 triggers)
   - Recalcula totales de compra cuando cambian items
   - **MIGRAR A:** `PurchaseService.recalculate_totals()`

6. **trg_create_transaction_from_purchase** (1 trigger)
   - Crea transacción financiera al crear compra
   - **MIGRAR A:** `PurchaseService.create_transaction()`

7. **trg_00_resolve_supplier** (2 triggers)
   - Busca/crea supplier por nombre
   - **MIGRAR A:** `PurchaseService.find_or_create_supplier()`

8. **trg_01_resolve_payment_account** (2 triggers)
   - Busca cuenta de pago para purchase
   - **MIGRAR A:** `PurchaseService.resolve_payment_account()`

9. **trg_01_deactivate_variants** (1 trigger)
   - Desactiva variantes cuando se desactiva producto
   - **MIGRAR A:** `ProductService.deactivate_product()`

10. **trg_01_validate_variant_active** (2 triggers)
    - Valida que producto padre esté activo
    - **MIGRAR A:** `ProductService.validate_variant()`

**Total a migrar:** ~14 triggers → **PurchaseService** (nuevo)

---

### FINANCE (15 triggers pendientes)
**Prioridad: ALTA** (gestión multi-moneda y lotes FIFO)

#### CRÍTICOS para multi-moneda:
11. **trg_10_update_balances** (1 trigger)
    - Actualiza balances de cuentas tras transacción
    - **MIGRAR A:** `FinanceService.update_balances()`

12. **trg_01_validate_currencies** (2 triggers)
    - Valida que monedas de from/to accounts sean iguales
    - **MIGRAR A:** `FinanceService.validate_transaction()`

13. **trg_02_validate_sufficient_balance** (1 trigger)
    - Valida saldo suficiente antes de transacción
    - **MIGRAR A:** `FinanceService.validate_balance()`

14. **trg_11_consume_lots_fifo** (1 trigger)
    - Consume lotes de moneda FIFO al hacer transacción
    - **MIGRAR A:** `FinanceService.consume_lots_fifo()`

15. **trg_12_create_currency_lot** (1 trigger)
    - Crea lote de moneda al recibir fondos
    - **MIGRAR A:** `FinanceService.create_currency_lot()`

16. **trg_recalcular_lote_tras_consumo** (3 triggers)
    - Recalcula cantidad restante en lote
    - **MIGRAR A:** `FinanceService.recalculate_lot()`

17. **trg_lots_validate_consistency** (1 trigger)
    - Valida consistencia de lote
    - **MIGRAR A:** `FinanceService.validate_lot()`

**Total a migrar:** ~11 triggers → **FinanceService** (nuevo)

---

### MARKETING (16 triggers pendientes)
**Prioridad: MEDIA** (analytics y métricas de ads)

#### CRÍTICOS para ROAS:
18. **trg_create_transaction_from_ads** (2 triggers)
    - Crea transacción de gasto publicitario
    - **MIGRAR A:** `MarketingService.create_ad_transaction()`

19. **trg_02_versions_close_previous** (1 trigger)
    - Cierra versión anterior al crear nueva
    - **MIGRAR A:** `MarketingService.create_version()`

20. **trg_01_versions_generate_number** (1 trigger)
    - Genera número secuencial de versión
    - **MIGRAR A:** `MarketingService.generate_version_number()`

**Total a migrar:** ~4 triggers → **MarketingService** (nuevo)

**Resto:** Triggers de timestamp y generación de IDs → Ya migrados

---

## PLAN DE IMPLEMENTACIÓN

### FASE 5: Purchase Service (ALTA PRIORIDAD)
**Tiempo estimado:** 2-3 horas
**Triggers a migrar:** 14

**Funcionalidades:**
- Crear compra completa (purchase + items)
- Sincronizar compra → inventario automáticamente
- Recalcular totales al modificar items
- Crear transacción financiera
- Find or create supplier
- Resolve payment account

**Archivo:** `app/services/purchase_service.py`

---

### FASE 6: Finance Service (ALTA PRIORIDAD)
**Tiempo estimado:** 3-4 horas
**Triggers a migrar:** 11

**Funcionalidades:**
- Gestión de multi-moneda (BOB, USD, EUR)
- Sistema FIFO de lotes de moneda
- Actualización de balances automática
- Validaciones de transacciones (moneda, saldo)
- Recálculo de lotes tras consumo

**Archivo:** `app/services/finance_service.py`

---

### FASE 7: Marketing Service (MEDIA PRIORIDAD)
**Tiempo estimado:** 1-2 horas
**Triggers a migrar:** 4

**Funcionalidades:**
- Crear transacciones de gasto publicitario
- Gestión de versiones de ads
- Cerrar versión anterior automáticamente

**Archivo:** `app/services/marketing_service.py`

---

### FASE 8: Validaciones Restantes (BAJA PRIORIDAD)
**Tiempo estimado:** 1 hora
**Triggers a migrar:** 3

**Funcionalidades:**
- Validaciones de producto/variante activos
- Desactivación en cascada de variantes

**Integración:** Agregar a `ProductService` existente

---

## ESTRATEGIA DE MIGRACIÓN

### 1. INCREMENTAL
- Migrar un schema a la vez (product → finance → marketing)
- Probar cada servicio antes de continuar
- Mantener triggers en BD durante transición (redundancia)

### 2. BACKWARDS COMPATIBLE
- Backend maneja toda la lógica
- Triggers en BD quedan como fallback (si backend falla)
- Desactivar triggers solo cuando backend esté 100% probado

### 3. TEST FIRST
- Escribir tests para cada servicio nuevo
- Probar casos edge (lotes FIFO, multi-moneda, etc.)
- Validar con datos reales

---

## BENEFICIOS DE LA MIGRACIÓN COMPLETA

### 1. MANTENIBILIDAD
- Lógica en Python (más fácil de leer/modificar que PL/pgSQL)
- Un solo lenguaje (Python vs Python + PostgreSQL)
- Debugging más fácil (logs detallados)

### 2. TESTABILIDAD
- Tests unitarios en Python (pytest)
- Mocking de base de datos
- CI/CD más sencillo

### 3. PERFORMANCE
- Menos round-trips a BD
- Transacciones más eficientes
- Caching en backend (futuro)

### 4. ESCALABILIDAD
- Lógica puede moverse a microservicios
- Horizontal scaling más fácil
- Preparado para arquitectura cloud

---

## PRÓXIMOS PASOS INMEDIATOS

1. ✅ **COMPLETADO:** Event listeners para timestamps (17 triggers)
2. ⏳ **EN PROGRESO:** PurchaseService (14 triggers)
3. ⏳ **PENDIENTE:** FinanceService (11 triggers)
4. ⏳ **PENDIENTE:** MarketingService (4 triggers)
5. ⏳ **PENDIENTE:** Validaciones restantes (3 triggers)

**TOTAL A MIGRAR:** 32 triggers adicionales
**TOTAL MIGRADO AL FINALIZAR:** 67 de 87 triggers (77%)

**Triggers que quedarán en BD:**
- ~20 triggers de utilidad general que no afectan lógica de negocio
- Se pueden mantener como están o migrar en futuro

---

## CONCLUSIÓN

Con la migración completa de las FASES 4-8, el backend de E-commerce BO será **100% independiente de los triggers de PostgreSQL** para TODA la lógica de negocio crítica.

**Sistema completamente funcional para:**
- ✅ Órdenes y tracking
- ✅ Inventario y movimientos
- ✅ Pagos semanales a carriers
- ⏳ Compras a proveedores (FASE 5)
- ⏳ Finanzas multi-moneda (FASE 6)
- ⏳ Métricas de marketing (FASE 7)

**Listo para producción:** ✅ (con FASES 1-4 completadas)
**Listo para funcionalidad completa:** 🔄 (requiere FASES 5-7)
