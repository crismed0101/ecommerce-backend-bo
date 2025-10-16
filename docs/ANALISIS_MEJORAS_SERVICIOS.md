# ANÁLISIS EXHAUSTIVO DE SERVICIOS - MEJORAS Y VALIDACIONES FALTANTES

**Fecha:** 15 de Octubre de 2025
**Objetivo:** Identificar validaciones faltantes, lógica incompleta, optimizaciones y mejoras por servicio

---

## 1. ORDER SERVICE

### ✅ Validaciones Implementadas
- External_order_id (idempotencia)
- Customer activo (is_active)
- Orden tiene items antes de cambiar a delivered/returned
- Stock suficiente antes de reducir inventario

### ❌ VALIDACIONES FALTANTES

#### 1.1 Validación de Transiciones de Estado
**PROBLEMA:** No hay validación de flujo de estados permitidos
```python
# Falta validar transiciones válidas
# Ejemplo: No se puede pasar de 'delivered' a 'new'
VALID_TRANSITIONS = {
    'new': ['confirmed', 'cancelled'],
    'confirmed': ['dispatched', 'cancelled'],
    'dispatched': ['delivered', 'returned', 'cancelled'],
    'delivered': ['returned'],  # Solo puede devolverse
    'returned': [],  # Estado final
    'cancelled': []  # Estado final
}
```

**IMPLEMENTACIÓN SUGERIDA:**
```python
@staticmethod
def validate_status_transition(old_status: str, new_status: str):
    """Validar que la transición de estado sea válida"""
    if new_status not in VALID_TRANSITIONS.get(old_status, []):
        raise ValueError(
            f"Transición inválida: {old_status} → {new_status}. "
            f"Transiciones permitidas: {VALID_TRANSITIONS.get(old_status, [])}"
        )
```

#### 1.2 Validación de Fechas Lógicas
**PROBLEMA:** No valida que created_at < updated_at
```python
# Agregar en update_status()
if tracking.updated_at and tracking.updated_at < tracking.created_at:
    raise ValueError("updated_at no puede ser anterior a created_at")
```

#### 1.3 Validación de Totales
**PROBLEMA:** No valida que la suma de items = total de orden
```python
@staticmethod
def validate_order_totals(db: Session, order_id: str):
    """Validar que suma de items = total de orden"""
    items_sum = db.query(func.sum(OrderItems.subtotal)).filter(
        OrderItems.order_id == order_id
    ).scalar() or Decimal('0')

    order = db.query(Orders).filter(Orders.order_id == order_id).first()

    if abs(items_sum - order.total) > Decimal('0.01'):
        raise ValueError(
            f"Inconsistencia en totales: suma items={items_sum}, "
            f"total orden={order.total}"
        )
```

#### 1.4 Validación de Customer con Múltiples Órdenes Activas
**PROBLEMA:** No hay límite de órdenes activas por customer
```python
# Agregar validación para evitar spam/fraude
MAX_ACTIVE_ORDERS_PER_CUSTOMER = 10

active_orders = db.query(Orders).join(OrderTracking).filter(
    Orders.customer_id == customer_id,
    OrderTracking.order_status.in_(['new', 'confirmed', 'dispatched'])
).count()

if active_orders >= MAX_ACTIVE_ORDERS_PER_CUSTOMER:
    raise ValueError(
        f"Cliente {customer_id} tiene {active_orders} órdenes activas. "
        f"Límite: {MAX_ACTIVE_ORDERS_PER_CUSTOMER}"
    )
```

### ❌ LÓGICA INCOMPLETA

#### 1.5 Cancelación de Órdenes con Reembolso
**FALTA:** Lógica para manejar órdenes canceladas que ya fueron pagadas
```python
@staticmethod
def cancel_order_with_refund(
    db: Session,
    order_id: str,
    refund_to_wallet_id: str,
    reason: str
):
    """
    Cancelar orden y generar reembolso si ya fue pagada

    Flujo:
    1. Validar que orden existe y puede cancelarse
    2. Si status = 'delivered' → restaurar inventario
    3. Si fue pagada → crear transacción de reembolso
    4. Actualizar order_tracking a 'cancelled'
    5. Agregar nota con razón de cancelación
    """
    # IMPLEMENTAR
    pass
```

#### 1.6 Órdenes Parciales (Entregas Parciales)
**FALTA:** Soporte para órdenes con múltiples items donde solo algunos se entregan
```python
# Tabla adicional requerida: order_item_tracking
# order_item_id | delivered_quantity | returned_quantity | status
```

#### 1.7 Historial de Cambios de Estado
**FALTA:** Log completo de todos los cambios de estado
```python
# Crear tabla: order_status_history
# order_id | old_status | new_status | changed_by | changed_at | notes
```

### ❌ CONSULTAS Y ORDENAMIENTO FALTANTE

#### 1.8 Métricas y Dashboards
**FALTAN:**
```python
@staticmethod
def get_order_stats_by_period(
    db: Session,
    date_from: date,
    date_to: date,
    group_by: str = 'day'  # day, week, month
) -> List[Dict]:
    """
    Estadísticas de órdenes por período

    Retorna:
    - Total órdenes
    - Órdenes por estado
    - Revenue total
    - AOV (Average Order Value)
    - Órdenes por departamento
    - Órdenes por carrier
    """
    pass

@staticmethod
def get_conversion_funnel(db: Session) -> Dict:
    """
    Embudo de conversión

    new -> confirmed -> dispatched -> delivered
    Calcular % de conversión en cada paso
    """
    pass

@staticmethod
def get_orders_by_utm_source(
    db: Session,
    date_from: date,
    date_to: date
) -> List[Dict]:
    """Órdenes agrupadas por fuente de tráfico (utm_source, utm_campaign)"""
    pass
```

#### 1.9 Búsqueda Avanzada
**FALTA:**
```python
@staticmethod
def search_orders(
    db: Session,
    query: str,
    search_in: List[str] = ['order_id', 'customer_name', 'customer_phone']
) -> List[Orders]:
    """
    Búsqueda full-text en órdenes

    Busca en:
    - order_id
    - external_order_id
    - customer.full_name
    - customer.phone
    - customer.email
    """
    pass
```

### ❌ PERFORMANCE Y OPTIMIZACIÓN

#### 1.10 Índices Faltantes
**RECOMENDACIÓN:** Agregar índices en PostgreSQL
```sql
-- Para búsquedas por external_order_id
CREATE INDEX idx_orders_external_order_id ON operations.orders(external_order_id);

-- Para filtrado por fechas
CREATE INDEX idx_orders_created_at ON operations.orders(created_at DESC);

-- Para búsquedas por customer
CREATE INDEX idx_orders_customer_id ON operations.orders(customer_id);

-- Índice compuesto para filtros comunes
CREATE INDEX idx_order_tracking_status_updated
ON operations.order_tracking(order_status, updated_at DESC);
```

#### 1.11 Paginación Mejorada (Cursor-based)
**PROBLEMA:** La paginación offset/limit es ineficiente con muchos registros
```python
@staticmethod
def get_orders_cursor_paginated(
    db: Session,
    cursor: Optional[str] = None,  # last order_id
    limit: int = 20
) -> Tuple[List[Orders], Optional[str]]:
    """
    Paginación cursor-based para mejor performance

    Returns:
        (orders, next_cursor)
    """
    query = db.query(Orders).order_by(Orders.created_at.desc(), Orders.order_id.desc())

    if cursor:
        # Obtener orden del cursor
        cursor_order = db.query(Orders).filter(Orders.order_id == cursor).first()
        if cursor_order:
            query = query.filter(
                (Orders.created_at < cursor_order.created_at) |
                ((Orders.created_at == cursor_order.created_at) &
                 (Orders.order_id < cursor_order.order_id))
            )

    orders = query.limit(limit + 1).all()

    next_cursor = None
    if len(orders) > limit:
        next_cursor = orders[limit - 1].order_id
        orders = orders[:limit]

    return (orders, next_cursor)
```

---

## 2. INVENTORY SERVICE

### ✅ Validaciones Implementadas
- Stock no negativo (doble validación)
- Idempotencia de movimientos (reference_id)
- Pessimistic locking (SELECT FOR UPDATE)

### ❌ VALIDACIONES FALTANTES

#### 2.1 Validación de Cantidad Mínima/Máxima
**FALTA:**
```python
# Agregar columnas a tabla inventory:
# min_stock_quantity (para alertas de stock bajo)
# max_stock_quantity (para evitar sobrestock)

@staticmethod
def validate_stock_limits(
    db: Session,
    variant_id: str,
    department: str,
    new_quantity: Decimal
):
    """Validar que stock esté entre límites configurados"""
    inventory = db.query(Inventory).filter(
        Inventory.product_variant_id == variant_id,
        Inventory.department == department
    ).first()

    if inventory.min_stock_quantity and new_quantity < inventory.min_stock_quantity:
        logger.warning(
            f"⚠️ Stock bajo: {variant_id} en {department}, "
            f"stock={new_quantity}, mínimo={inventory.min_stock_quantity}"
        )

    if inventory.max_stock_quantity and new_quantity > inventory.max_stock_quantity:
        raise ValueError(
            f"Stock excede máximo permitido: {new_quantity} > {inventory.max_stock_quantity}"
        )
```

#### 2.2 Validación de Movimientos Sospechosos
**FALTA:** Detección de movimientos anómalos
```python
@staticmethod
def detect_suspicious_movements(
    db: Session,
    variant_id: str,
    department: str,
    quantity: Decimal
) -> List[str]:
    """
    Detectar movimientos sospechosos

    Alertas:
    - Cantidad excesiva (>1000 unidades)
    - Movimientos duplicados en corto tiempo
    - Ajustes manuales frecuentes
    """
    warnings = []

    # Cantidad excesiva
    if abs(quantity) > 1000:
        warnings.append(f"Cantidad excesiva: {quantity}")

    # Movimientos recientes similares
    recent_count = db.query(InventoryMovements).filter(
        InventoryMovements.product_variant_id == variant_id,
        InventoryMovements.department == department,
        InventoryMovements.movement_date >= datetime.now() - timedelta(hours=1)
    ).count()

    if recent_count > 10:
        warnings.append(f"Demasiados movimientos recientes: {recent_count} en última hora")

    return warnings
```

### ❌ LÓGICA INCOMPLETA

#### 2.3 Transferencias Entre Departamentos
**FALTA:**
```python
@staticmethod
def transfer_stock_between_departments(
    db: Session,
    variant_id: str,
    from_department: str,
    to_department: str,
    quantity: Decimal,
    transfer_id: str,
    notes: Optional[str] = None
):
    """
    Transferir stock entre departamentos

    Flujo:
    1. Validar stock suficiente en origen
    2. Reducir stock en from_department (movement_type='transfer_out')
    3. Aumentar stock en to_department (movement_type='transfer_in')
    4. Crear registro en tabla transfers (tracking)
    """
    # Validar stock origen
    if not InventoryService.validate_stock(db, variant_id, from_department, quantity):
        raise ValueError(f"Stock insuficiente en {from_department}")

    # Movimiento salida
    InventoryService.create_movement(
        db=db,
        variant_id=variant_id,
        department=from_department,
        movement_type='transfer_out',
        quantity=-quantity,
        reference_id=transfer_id
    )

    # Movimiento entrada
    InventoryService.create_movement(
        db=db,
        variant_id=variant_id,
        department=to_department,
        movement_type='transfer_in',
        quantity=quantity,
        reference_id=transfer_id
    )

    logger.info(
        f"✅ Transferencia completada: {quantity} unidades de {variant_id} "
        f"desde {from_department} a {to_department}"
    )
```

#### 2.4 Ajustes de Inventario con Auditoría
**FALTA:**
```python
@staticmethod
def create_inventory_adjustment(
    db: Session,
    variant_id: str,
    department: str,
    adjustment_quantity: Decimal,
    reason: str,
    adjusted_by: str,  # user_id o sistema
    notes: Optional[str] = None
):
    """
    Ajuste manual de inventario con auditoría

    Casos de uso:
    - Corrección de errores de conteo
    - Pérdida de mercancía
    - Productos dañados
    """
    adjustment_id = IDGenerator.generate_adjustment_id(db)

    # Crear movimiento
    movement = InventoryService.create_movement(
        db=db,
        variant_id=variant_id,
        department=department,
        movement_type='adjustment',
        quantity=adjustment_quantity,
        reference_id=adjustment_id
    )

    # Registrar en tabla de auditoría
    adjustment = InventoryAdjustments(
        adjustment_id=adjustment_id,
        movement_id=movement.movement_id,
        reason=reason,
        adjusted_by=adjusted_by,
        notes=notes,
        created_at=datetime.now()
    )
    db.add(adjustment)
    db.flush()

    logger.info(
        f"✅ Ajuste de inventario: {adjustment_quantity} unidades de {variant_id} "
        f"en {department}, razón: {reason}, por: {adjusted_by}"
    )
```

### ❌ CONSULTAS Y REPORTES FALTANTES

#### 2.5 Alertas de Stock Bajo
**FALTA:**
```python
@staticmethod
def get_low_stock_alerts(
    db: Session,
    threshold_percentage: int = 20  # 20% del mínimo
) -> List[Dict]:
    """
    Obtener productos con stock bajo

    Retorna productos donde:
    stock_quantity < min_stock_quantity * (threshold_percentage / 100)
    """
    query = text("""
        SELECT
            pv.product_variant_id,
            pv.variant_name,
            pv.sku,
            i.department,
            i.stock_quantity,
            i.min_stock_quantity,
            ROUND((i.stock_quantity::numeric / i.min_stock_quantity::numeric * 100), 2) as stock_percentage
        FROM product.inventory i
        JOIN product.product_variants pv ON i.product_variant_id = pv.product_variant_id
        WHERE i.min_stock_quantity > 0
          AND i.stock_quantity < (i.min_stock_quantity * :threshold)
        ORDER BY stock_percentage ASC
    """)

    results = db.execute(query, {'threshold': threshold_percentage / 100}).fetchall()

    return [
        {
            'variant_id': r[0],
            'variant_name': r[1],
            'sku': r[2],
            'department': r[3],
            'current_stock': int(r[4]),
            'min_stock': int(r[5]),
            'stock_percentage': float(r[6])
        }
        for r in results
    ]
```

#### 2.6 Reporte de Rotación de Inventario
**FALTA:**
```python
@staticmethod
def get_inventory_turnover_rate(
    db: Session,
    variant_id: Optional[str] = None,
    date_from: date = None,
    date_to: date = None
) -> List[Dict]:
    """
    Calcular tasa de rotación de inventario

    Fórmula:
    Turnover Rate = Total Ventas / Stock Promedio

    Alto turnover = producto se vende rápido
    Bajo turnover = producto se mueve lento (posible dead stock)
    """
    pass
```

#### 2.7 Valorización de Inventario
**FALTA:**
```python
@staticmethod
def get_inventory_valuation(
    db: Session,
    department: Optional[str] = None,
    valuation_method: str = 'last_purchase_cost'  # FIFO, LIFO, average
) -> Dict:
    """
    Calcular valor total del inventario

    Métodos:
    - last_purchase_cost: Usar último costo de compra
    - fifo: First In First Out
    - average: Costo promedio ponderado

    Retorna:
    - Total unidades
    - Valor total
    - Valor por departamento
    """
    pass
```

---

## 3. PRODUCT SERVICE

### ✅ Validaciones Implementadas
- Producto padre activo antes de activar variante
- Búsqueda en cascada (shopify_variant_id → sku → name)
- Auto-generación de SKU único

### ❌ VALIDACIONES FALTANTES

#### 3.1 Validación de SKU Duplicados Global
**PROBLEMA:** El SKU es único pero no hay validación cross-check
```python
@staticmethod
def validate_sku_unique(db: Session, sku: str, exclude_variant_id: Optional[str] = None):
    """Validar que SKU sea único en toda la base de datos"""
    query = db.query(ProductVariants).filter(ProductVariants.sku == sku)

    if exclude_variant_id:
        query = query.filter(ProductVariants.product_variant_id != exclude_variant_id)

    existing = query.first()

    if existing:
        raise ValueError(
            f"SKU {sku} ya existe en variante {existing.product_variant_id} "
            f"({existing.variant_name})"
        )
```

#### 3.2 Validación de Precios
**FALTA:**
```python
# Agregar columnas a product_variants:
# base_price (precio base)
# sale_price (precio en oferta, opcional)
# min_allowed_price (precio mínimo permitido)
# max_allowed_price (precio máximo permitido)

@staticmethod
def validate_price_range(
    base_price: Decimal,
    sale_price: Optional[Decimal],
    min_allowed: Decimal,
    max_allowed: Decimal
):
    """Validar que precios estén en rango permitido"""
    if base_price < min_allowed or base_price > max_allowed:
        raise ValueError(
            f"Precio base {base_price} fuera de rango "
            f"({min_allowed} - {max_allowed})"
        )

    if sale_price and sale_price >= base_price:
        raise ValueError(
            f"Precio de oferta {sale_price} debe ser menor que "
            f"precio base {base_price}"
        )
```

### ❌ LÓGICA INCOMPLETA

#### 3.3 Historial de Precios
**FALTA:**
```python
# Tabla: product_price_history
# variant_id | old_price | new_price | changed_at | changed_by | reason

@staticmethod
def update_variant_price(
    db: Session,
    variant_id: str,
    new_price: Decimal,
    changed_by: str,
    reason: str
):
    """
    Actualizar precio de variante con historial

    1. Obtener precio actual
    2. Guardar en price_history
    3. Actualizar precio actual
    """
    pass
```

#### 3.4 Productos Relacionados / Upselling
**FALTA:**
```python
# Tabla: product_relations
# product_id | related_product_id | relation_type (cross_sell, upsell, bundle)

@staticmethod
def set_related_products(
    db: Session,
    product_id: str,
    related_product_ids: List[str],
    relation_type: str = 'cross_sell'
):
    """Establecer productos relacionados para upselling/cross-selling"""
    pass

@staticmethod
def get_recommended_products(
    db: Session,
    product_id: str,
    limit: int = 5
) -> List[Products]:
    """Obtener productos recomendados basados en relaciones"""
    pass
```

#### 3.5 Variantes con Atributos (Color, Talla, etc.)
**FALTA:**
```python
# Tabla: variant_attributes
# variant_id | attribute_name (color, size, material) | attribute_value

@staticmethod
def create_variant_with_attributes(
    db: Session,
    product_id: str,
    variant_name: str,
    sku: str,
    attributes: Dict[str, str]  # {'color': 'Rojo', 'size': 'M'}
):
    """Crear variante con atributos estructurados"""
    pass
```

### ❌ CONSULTAS FALTANTES

#### 3.6 Búsqueda con Filtros Avanzados
**FALTA:**
```python
@staticmethod
def search_products_advanced(
    db: Session,
    query: Optional[str] = None,
    category: Optional[str] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    in_stock_only: bool = False,
    department: Optional[str] = None,
    sort_by: str = 'name',  # name, price, created_at
    sort_order: str = 'asc'
) -> List[ProductVariants]:
    """
    Búsqueda avanzada de productos con múltiples filtros

    Filtros:
    - Texto (nombre, SKU, categoría)
    - Rango de precios
    - Solo con stock
    - Por departamento
    - Ordenamiento flexible
    """
    pass
```

#### 3.7 Productos Más Vendidos
**FALTA:**
```python
@staticmethod
def get_top_selling_products(
    db: Session,
    date_from: date,
    date_to: date,
    limit: int = 10,
    department: Optional[str] = None
) -> List[Dict]:
    """
    Top productos más vendidos en período

    Retorna:
    - variant_id
    - variant_name
    - total_quantity_sold
    - total_revenue
    - order_count
    """
    query = text("""
        SELECT
            pv.product_variant_id,
            pv.variant_name,
            pv.sku,
            SUM(oi.quantity) as total_quantity,
            SUM(oi.subtotal) as total_revenue,
            COUNT(DISTINCT oi.order_id) as order_count
        FROM operations.order_items oi
        JOIN product.product_variants pv ON oi.product_variant_id = pv.product_variant_id
        JOIN operations.orders o ON oi.order_id = o.order_id
        JOIN operations.order_tracking ot ON o.order_id = ot.order_id
        WHERE ot.order_status = 'delivered'
          AND o.created_at BETWEEN :date_from AND :date_to
        GROUP BY pv.product_variant_id, pv.variant_name, pv.sku
        ORDER BY total_quantity DESC
        LIMIT :limit
    """)

    results = db.execute(query, {
        'date_from': date_from,
        'date_to': date_to,
        'limit': limit
    }).fetchall()

    return [...]
```

---

## 4. PAYMENT SERVICE

### ✅ Validaciones Implementadas
- Carrier activo antes de procesar pago
- Balance anterior (arrastre de saldo negativo)
- Idempotencia de payment_orders

### ❌ VALIDACIONES FALTANTES

#### 4.1 Validación de Montos Negativos Excesivos
**FALTA:**
```python
# Si un carrier tiene balance negativo > -10000 BOB por más de 2 semanas
# → alertar o bloquear

@staticmethod
def validate_excessive_negative_balance(
    db: Session,
    carrier_id: str,
    current_balance: Decimal
):
    """Validar que balance negativo no sea excesivo"""
    NEGATIVE_BALANCE_THRESHOLD = Decimal('-10000')

    if current_balance < NEGATIVE_BALANCE_THRESHOLD:
        # Contar semanas consecutivas con balance negativo
        negative_weeks = db.query(Payments).filter(
            Payments.carrier_id == carrier_id,
            Payments.total_final_amount < 0,
            Payments.week_start_date >= datetime.now().date() - timedelta(weeks=4)
        ).order_by(Payments.week_start_date.desc()).all()

        if len(negative_weeks) >= 2:
            raise ValueError(
                f"Carrier {carrier_id} tiene balance negativo excesivo "
                f"({current_balance} BOB) durante {len(negative_weeks)} semanas"
            )
```

#### 4.2 Validación de Pagos Duplicados
**FALTA:**
```python
@staticmethod
def validate_no_duplicate_payment(
    db: Session,
    carrier_id: str,
    week_start: date
):
    """Validar que no exista payment marcado como 'paid' para la misma semana"""
    existing_paid = db.query(Payments).filter(
        Payments.carrier_id == carrier_id,
        Payments.week_start_date == week_start,
        Payments.payment_status == 'paid'
    ).first()

    if existing_paid:
        raise ValueError(
            f"Ya existe payment pagado para carrier {carrier_id} "
            f"en semana {week_start}: {existing_paid.payment_id}"
        )
```

### ❌ LÓGICA INCOMPLETA

#### 4.3 Procesamiento por Lotes (Batch Payment)
**FALTA:**
```python
@staticmethod
def process_batch_payment(
    db: Session,
    carrier_id: str,
    payment_ids: List[str],
    wallet_id: str,
    paid_date: date
):
    """
    Marcar múltiples payments como pagados en un solo lote

    Casos de uso:
    - Pagar múltiples semanas juntas
    - Pagar saldo acumulado de varias semanas
    """
    total_amount = Decimal('0')

    for payment_id in payment_ids:
        payment = db.query(Payments).filter(
            Payments.payment_id == payment_id
        ).first()

        if not payment:
            raise ValueError(f"Payment {payment_id} no encontrado")

        if payment.payment_status == 'paid':
            raise ValueError(f"Payment {payment_id} ya está pagado")

        payment.payment_status = 'paid'
        payment.paid_date = paid_date
        payment.received_in_wallet_id = wallet_id

        total_amount += payment.total_final_amount

        # Crear transacción financiera
        PaymentService.create_transaction_from_payment(
            db=db,
            payment=payment,
            old_status='pending'
        )

    db.commit()

    logger.info(
        f"✅ Batch payment procesado: {len(payment_ids)} payments, "
        f"total={total_amount} BOB, carrier={carrier_id}"
    )

    return total_amount
```

#### 4.4 Anticipos y Préstamos
**FALTA:**
```python
# Tabla: carrier_advances
# advance_id | carrier_id | amount | advance_date | status | repayment_plan

@staticmethod
def create_carrier_advance(
    db: Session,
    carrier_id: str,
    amount: Decimal,
    repayment_weeks: int = 4
):
    """
    Crear anticipo para carrier

    El anticipo se descuenta automáticamente de payments futuros
    """
    pass
```

### ❌ REPORTES FALTANTES

#### 4.5 Reporte de Comisiones por Carrier
**FALTA:**
```python
@staticmethod
def get_carrier_commission_report(
    db: Session,
    date_from: date,
    date_to: date
) -> List[Dict]:
    """
    Reporte de comisiones ganadas por carrier

    Agrupa:
    - Total entregas
    - Total devoluciones
    - Comisiones totales
    - Balance final
    """
    query = text("""
        SELECT
            c.carrier_id,
            c.full_name,
            COUNT(DISTINCT p.payment_id) as total_weeks,
            SUM(p.total_deliveries) as total_deliveries,
            SUM(p.total_deliveries_amount) as total_delivery_amount,
            SUM(p.total_returns) as total_returns,
            SUM(p.total_returns_amount) as total_return_amount,
            SUM(p.total_net_amount) as total_net,
            SUM(p.total_final_amount) as total_final
        FROM operations.carriers c
        JOIN operations.payments p ON c.carrier_id = p.carrier_id
        WHERE p.week_start_date BETWEEN :date_from AND :date_to
        GROUP BY c.carrier_id, c.full_name
        ORDER BY total_final DESC
    """)

    results = db.execute(query, {
        'date_from': date_from,
        'date_to': date_to
    }).fetchall()

    return [...]
```

---

## 5. PURCHASE SERVICE

### ✅ Validaciones Implementadas
- Find_or_create_supplier
- Recalcular totales desde items
- Creación automática de transacción financiera

### ❌ VALIDACIONES FALTANTES

#### 5.1 Validación de Precios de Compra
**FALTA:**
```python
@staticmethod
def validate_purchase_price(
    db: Session,
    variant_id: str,
    unit_cost: Decimal
):
    """
    Validar que precio de compra sea razonable

    Alertas si:
    - Precio > 200% del último precio de compra
    - Precio < 50% del último precio de compra
    """
    last_purchase = db.query(PurchaseItems).filter(
        PurchaseItems.product_variant_id == variant_id
    ).order_by(PurchaseItems.created_at.desc()).first()

    if last_purchase:
        price_change_pct = (unit_cost - last_purchase.unit_cost) / last_purchase.unit_cost * 100

        if abs(price_change_pct) > 100:
            logger.warning(
                f"⚠️ Cambio significativo en precio de compra: {variant_id}, "
                f"último={last_purchase.unit_cost}, actual={unit_cost}, "
                f"cambio={price_change_pct:.1f}%"
            )
```

#### 5.2 Validación de Supplier Activo
**FALTA:**
```python
# Agregar columna a suppliers: is_active

@staticmethod
def validate_supplier_active(db: Session, supplier_id: str):
    """Validar que supplier esté activo antes de crear purchase"""
    supplier = db.query(Suppliers).filter(
        Suppliers.supplier_id == supplier_id
    ).first()

    if not supplier or not supplier.is_active:
        raise ValueError(
            f"Supplier {supplier_id} está inactivo. "
            f"No se pueden crear compras."
        )
```

### ❌ LÓGICA INCOMPLETA

#### 5.3 Órdenes de Compra (Purchase Orders)
**FALTA:**
```python
# Tabla: purchase_orders
# po_id | supplier_id | status (draft, sent, confirmed, received, cancelled)
# expected_delivery_date | total_expected

@staticmethod
def create_purchase_order(
    db: Session,
    supplier_id: str,
    items: List[Dict],
    expected_delivery_date: date
):
    """
    Crear orden de compra (antes de recibir mercancía)

    Estados:
    - draft: Borrador
    - sent: Enviada al supplier
    - confirmed: Confirmada por supplier
    - received: Mercancía recibida (convierte en Purchase)
    - cancelled: Cancelada
    """
    pass
```

#### 5.4 Devoluciones a Proveedores
**FALTA:**
```python
@staticmethod
def create_supplier_return(
    db: Session,
    purchase_id: str,
    items: List[Dict],  # items a devolver
    reason: str
):
    """
    Devolver mercancía a proveedor

    Flujo:
    1. Validar que items pertenezcan a purchase
    2. Reducir inventario
    3. Crear purchase_return
    4. Crear transacción financiera de reembolso (opcional)
    """
    pass
```

### ❌ REPORTES FALTANTES

#### 5.5 Análisis de Proveedores
**FALTA:**
```python
@staticmethod
def get_supplier_performance(
    db: Session,
    supplier_id: str,
    date_from: date,
    date_to: date
) -> Dict:
    """
    Performance de supplier

    Métricas:
    - Total compras
    - Total gastado
    - Productos únicos comprados
    - Frecuencia de compras
    - Variación de precios
    """
    pass
```

---

## 6. FINANCE SERVICE

### ✅ Validaciones Implementadas
- Validación de monedas (from/to deben coincidir)
- Validación de saldo suficiente
- Sistema FIFO completo
- Recalculo idempotente de lotes

### ❌ VALIDACIONES FALTANTES

#### 6.1 Límites de Transacciones
**FALTA:**
```python
# Agregar validaciones de límites
MAX_TRANSACTION_AMOUNT = {
    'BOB': Decimal('100000'),
    'USD': Decimal('15000'),
    'EUR': Decimal('13000')
}

@staticmethod
def validate_transaction_limit(amount: Decimal, currency: str):
    """Validar que transacción no exceda límite"""
    max_amount = MAX_TRANSACTION_AMOUNT.get(currency, Decimal('100000'))

    if amount > max_amount:
        raise ValueError(
            f"Transacción excede límite: {amount} {currency} > {max_amount} {currency}"
        )
```

#### 6.2 Validación de Cuentas Congeladas
**FALTA:**
```python
# Agregar columna a accounts: is_frozen, frozen_reason

@staticmethod
def validate_account_not_frozen(db: Session, account_id: str):
    """Validar que cuenta no esté congelada"""
    account = db.query(Accounts).filter(
        Accounts.account_id == account_id
    ).first()

    if account.is_frozen:
        raise ValueError(
            f"Cuenta {account_id} está congelada. "
            f"Razón: {account.frozen_reason}"
        )
```

### ❌ LÓGICA INCOMPLETA

#### 6.3 Conversión de Monedas
**FALTA:**
```python
# Tabla: exchange_rates
# from_currency | to_currency | rate | effective_date

@staticmethod
def convert_currency(
    db: Session,
    from_account_id: str,
    to_account_id: str,
    amount: Decimal,
    from_currency: str,
    to_currency: str
):
    """
    Convertir moneda entre cuentas de diferentes monedas

    Flujo:
    1. Obtener tasa de cambio actual
    2. Calcular monto convertido
    3. Crear transacción de salida (from_account)
    4. Crear transacción de entrada (to_account)
    5. Registrar conversión en currency_exchanges
    """
    pass
```

#### 6.4 Conciliación Bancaria
**FALTA:**
```python
@staticmethod
def reconcile_account(
    db: Session,
    account_id: str,
    bank_balance: Decimal,
    reconciliation_date: date
):
    """
    Conciliar saldo de cuenta con extracto bancario

    Compara:
    - Balance calculado en sistema
    - Balance reportado por banco
    - Identifica diferencias
    """
    system_balance = FinanceService.get_account_balance(db, account_id)[0]

    difference = system_balance - bank_balance

    if abs(difference) > Decimal('0.01'):
        logger.error(
            f"❌ Descuadre en cuenta {account_id}: "
            f"sistema={system_balance}, banco={bank_balance}, "
            f"diferencia={difference}"
        )

        # Crear alerta de descuadre
        # ...

    return {
        'system_balance': system_balance,
        'bank_balance': bank_balance,
        'difference': difference,
        'reconciled': abs(difference) <= Decimal('0.01')
    }
```

### ❌ REPORTES FALTANTES

#### 6.5 Estado de Resultados (P&L)
**FALTA:**
```python
@staticmethod
def get_profit_and_loss(
    db: Session,
    date_from: date,
    date_to: date
) -> Dict:
    """
    Estado de Resultados (Profit & Loss)

    Ingresos:
    - Ventas
    - Otros ingresos

    Egresos:
    - Costo de ventas
    - Gastos operativos
    - Gastos administrativos
    - Impuestos

    Resultado = Ingresos - Egresos
    """
    pass
```

#### 6.6 Flujo de Caja
**FALTA:**
```python
@staticmethod
def get_cash_flow(
    db: Session,
    date_from: date,
    date_to: date,
    account_id: Optional[str] = None
) -> Dict:
    """
    Flujo de caja (Cash Flow)

    - Entradas de efectivo (income)
    - Salidas de efectivo (expenses)
    - Saldo final
    """
    pass
```

---

## 7. MARKETING SERVICE

### ✅ Validaciones Implementadas
- Creación de ads con gasto inicial
- Versionamiento de ads (A/B testing)
- Cálculo automático de CTR, CPC, ROAS

### ❌ VALIDACIONES FALTANTES

#### 7.1 Validación de Presupuesto Diario
**FALTA:**
```python
@staticmethod
def validate_daily_budget_not_exceeded(
    db: Session,
    ad_id: str,
    date: date,
    new_spend: Decimal
):
    """
    Validar que gasto diario no exceda daily_budget configurado
    """
    ad = db.query(Ads).filter(Ads.ad_id == ad_id).first()

    if not ad.daily_budget:
        return  # Sin límite

    # Calcular gasto total del día
    total_spent_today = db.query(
        func.sum(AdDailyMetrics.spend)
    ).filter(
        AdDailyMetrics.ad_id == ad_id,
        AdDailyMetrics.metrics_date == date
    ).scalar() or Decimal('0')

    if (total_spent_today + new_spend) > ad.daily_budget:
        raise ValueError(
            f"Presupuesto diario excedido para ad {ad_id}: "
            f"gastado={total_spent_today}, nuevo={new_spend}, "
            f"límite={ad.daily_budget}"
        )
```

#### 7.2 Validación de Campañas Activas
**FALTA:**
```python
@staticmethod
def validate_campaign_active(db: Session, campaign_id: str):
    """Validar que campaña esté activa antes de crear ads"""
    campaign = db.query(Campaigns).filter(
        Campaigns.campaign_id == campaign_id
    ).first()

    if not campaign or campaign.status != 'active':
        raise ValueError(
            f"Campaña {campaign_id} no está activa. "
            f"No se pueden crear ads."
        )
```

### ❌ LÓGICA INCOMPLETA

#### 7.3 Optimización Automática de Presupuesto
**FALTA:**
```python
@staticmethod
def auto_optimize_budget(
    db: Session,
    campaign_id: str
):
    """
    Redistribuir presupuesto entre ads según performance

    Algoritmo:
    1. Obtener todos los ads de la campaña
    2. Calcular ROAS de cada ad
    3. Aumentar presupuesto en ads con ROAS alto
    4. Reducir presupuesto en ads con ROAS bajo
    5. Pausar ads con ROAS < 1 (pérdida)
    """
    pass
```

#### 7.4 Atribución Multi-Touch
**FALTA:**
```python
@staticmethod
def calculate_attribution(
    db: Session,
    order_id: str,
    attribution_model: str = 'last_click'  # first_click, linear, time_decay
):
    """
    Calcular atribución de conversión a campañas/ads

    Modelos:
    - last_click: 100% al último click
    - first_click: 100% al primer click
    - linear: Dividir equitativamente
    - time_decay: Más peso a clicks recientes
    """
    pass
```

### ❌ REPORTES FALTANTES

#### 7.5 Comparación de Variantes A/B
**FALTA:**
```python
@staticmethod
def compare_ab_test_variants(
    db: Session,
    ad_id: str
) -> Dict:
    """
    Comparar performance de variantes de un ad

    Retorna:
    - Versión ganadora (mayor ROAS)
    - Diferencia estadística
    - Recomendación (continuar test, declarar ganador, pausar perdedor)
    """
    pass
```

---

## RESUMEN DE PRIORIDADES

### 🔴 CRÍTICO (Implementar YA)
1. **OrderService:** Validación de transiciones de estado
2. **OrderService:** Validación de totales (suma items = total orden)
3. **InventoryService:** Transferencias entre departamentos
4. **PaymentService:** Validación de pagos duplicados
5. **FinanceService:** Límites de transacciones

### 🟡 IMPORTANTE (Implementar pronto)
1. **OrderService:** Cancelación con reembolso
2. **InventoryService:** Alertas de stock bajo
3. **ProductService:** Historial de precios
4. **PaymentService:** Procesamiento por lotes
5. **PurchaseService:** Validación de precios

### 🟢 MEJORAS (Nice to have)
1. **OrderService:** Métricas y dashboards
2. **InventoryService:** Valorización de inventario
3. **ProductService:** Productos relacionados
4. **MarketingService:** Optimización automática
5. **FinanceService:** Estado de resultados

---

**FIN DEL ANÁLISIS**
