"""
OrderService - Gestión de órdenes completas

Responsabilidades:
1. Crear orden completa (customer + order + items + tracking)
2. Actualizar estado de orden
3. Gestionar inventario cuando se entrega/devuelve
4. Actualizar estadísticas de clientes
5. IDEMPOTENCY: Verificar external_order_id antes de crear

Principios:
- ACID: Transacciones atómicas (rollback si algo falla)
- ORCHESTRATION: Coordina ProductService, InventoryService
- SOLID: Responsabilidad única (solo órdenes)
- DRY: Reutiliza servicios existentes

REEMPLAZA TODA LA LÓGICA DE TRIGGERS:
- fn_generate_order_id → IDGenerator
- fn_generate_customer_id → IDGenerator
- fn_auto_create_order_tracking → OrderService.create_full_order()
- fn_update_customer_stats → OrderService._update_customer_stats()
- fn_manage_inventory_from_delivery → OrderService.update_status() + InventoryService
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import logging

from app.models import Customers, Orders, OrderItems, OrderTracking
from app.services.id_generator import IDGenerator
from app.services.product_service import ProductService
from app.services.inventory_service import InventoryService
from app.services.delivery_cost_service import DeliveryCostService
from app.services.payment_service import PaymentService
from app.schemas.order import OrderCreate, OrderCreateResponse, OrderStatusEnum

logger = logging.getLogger(__name__)


class OrderService:
    """
    Service para gestión de órdenes

    FLUJO COMPLETO:
    1. Verificar idempotencia (external_order_id)
    2. Buscar o crear customer
    3. Buscar o crear product variants (ProductService)
    4. Crear orden + items + tracking
    5. Actualizar customer stats
    6. (NO reducir inventario todavía - solo al entregar)
    """

    # ==================== CREAR ORDEN COMPLETA ====================

    @staticmethod
    def create_full_order(
        db: Session,
        order_data: OrderCreate
    ) -> OrderCreateResponse:
        """
        Crear orden completa (TRANSACCIÓN ATÓMICA)

        IDEMPOTENCIA:
        - Si external_order_id ya existe → retornar orden existente
        - Si no → crear nueva orden

        Args:
            db: Database session
            order_data: Datos de la orden (OrderCreate schema)

        Returns:
            OrderCreateResponse con info de la orden creada
        """

        try:
            # PASO 1: IDEMPOTENCY CHECK
            if order_data.external_order_id:
                existing_order = db.query(Orders).filter(
                    Orders.external_order_id == order_data.external_order_id
                ).first()

                if existing_order:
                    logger.info(f"🔄 IDEMPOTENCY: Orden ya existe (external_id={order_data.external_order_id})")
                    return OrderCreateResponse(
                        success=True,
                        order_id=existing_order.order_id,
                        customer_id=existing_order.customer_id,
                        total_items=len(existing_order.order_items),
                        total_amount=float(existing_order.total),
                        message="Orden ya existía (idempotencia)",
                        products_created=0,
                        warnings=["Orden duplicada - ya procesada previamente"]
                    )

            # PASO 2: Buscar o crear customer
            customer = OrderService._find_or_create_customer(db, order_data.customer)

            # PASO 3: Buscar o crear product variants (USA ProductService)
            variants_info = []  # Lista de (variant, was_created, item_data)
            for item_data in order_data.items:
                variant, was_created = ProductService.find_or_create_variant(
                    db=db,
                    shopify_product_id=item_data.shopify_product_id,
                    shopify_variant_id=item_data.shopify_variant_id,
                    product_name=item_data.product_name,
                    sku=item_data.sku
                )
                variants_info.append((variant, was_created, item_data))

            # PASO 4: Crear orden
            order_id = IDGenerator.generate_order_id(db)

            order = Orders(
                order_id=order_id,
                customer_id=customer.customer_id,
                total=order_data.total,
                carrier_id=order_data.carrier_id,
                is_priority_shipping=order_data.is_priority_shipping,
                priority_shipping_cost=order_data.priority_shipping_cost,
                utm_source=order_data.utm_source,
                utm_medium=order_data.utm_medium,
                utm_campaign=order_data.utm_campaign,
                utm_content=order_data.utm_content,
                utm_term=order_data.utm_term,
                external_order_id=order_data.external_order_id,
                notes=order_data.notes
            )

            db.add(order)
            db.flush()

            logger.info(f"✅ Orden creada: {order_id} (customer={customer.customer_id})")

            # PASO 5: Crear order items
            for item_number, (variant, was_created, item_data) in enumerate(variants_info, start=1):
                subtotal = item_data.quantity * item_data.unit_price

                # Generar order_item_id
                order_item_id = IDGenerator.generate_order_item_id(db, order_id, item_number)

                order_item = OrderItems(
                    order_item_id=order_item_id,
                    order_id=order_id,
                    product_variant_id=variant.product_variant_id,
                    product_name=item_data.product_name,  # Guardar nombre histórico
                    quantity=item_data.quantity,
                    unit_price=item_data.unit_price,
                    subtotal=subtotal
                )

                db.add(order_item)

            logger.info(f"✅ {len(variants_info)} items creados para orden {order_id}")

            # PASO 5.1: VALIDACIÓN DE TOTALES (CRÍTICA)
            db.flush()  # Flush para que los items estén disponibles para la validación
            OrderService.validate_order_totals(db, order_id)

            # PASO 5.2: VALIDACIÓN ANTI-DUPLICADOS 24H (CRÍTICA)
            OrderService.validate_no_duplicate_order_24h(db, customer.customer_id, order_data.items)

            # PASO 6: Crear order_tracking (estado inicial: "new")
            # IDEMPOTENCIA: Verificar si ya existe (puede ser creado por trigger de BD)
            tracking = db.query(OrderTracking).filter(
                OrderTracking.order_id == order_id
            ).first()

            if not tracking:
                tracking = OrderTracking(
                    order_id=order_id,
                    order_status="new"
                )
                db.add(tracking)
                logger.info(f"✅ Tracking creado para orden {order_id} (status=new)")
            else:
                logger.info(f"🔄 Tracking ya existe para orden {order_id} (creado por BD trigger)")

            # PASO 7: Actualizar customer stats
            OrderService._update_customer_stats(db, customer.customer_id, order_data.total)

            # COMMIT
            db.commit()

            # Preparar response
            products_created = sum(1 for _, was_created, _ in variants_info if was_created)
            warnings = []

            if products_created > 0:
                warnings.append(f"{products_created} productos fueron auto-creados")

            return OrderCreateResponse(
                success=True,
                order_id=order_id,
                customer_id=customer.customer_id,
                total_items=len(variants_info),
                total_amount=float(order_data.total),
                message=f"Orden creada exitosamente: {order_id}",
                products_created=products_created,
                warnings=warnings
            )

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error creando orden: {str(e)}")
            raise ValueError(f"Error creando orden: {str(e)}")

    # ==================== ACTUALIZAR ESTADO ====================

    @staticmethod
    def update_status(
        db: Session,
        order_id: str,
        new_status: OrderStatusEnum,
        notes: Optional[str] = None
    ) -> OrderTracking:
        """
        Actualizar estado de orden

        LÓGICA CRÍTICA:
        - Si new_status = "delivered" → Reducir inventario (USA InventoryService)
        - Si new_status = "returned" → Aumentar inventario (USA InventoryService)
        - Si new_status = "cancelled" → No hacer nada con inventario

        Returns:
            OrderTracking actualizado
        """

        try:
            # Buscar orden
            order = db.query(Orders).filter(Orders.order_id == order_id).first()

            if not order:
                raise ValueError(f"Orden no encontrada: {order_id}")

            # Buscar tracking
            tracking = db.query(OrderTracking).filter(
                OrderTracking.order_id == order_id
            ).first()

            if not tracking:
                raise ValueError(f"Tracking no encontrado para orden: {order_id}")

            old_status = tracking.order_status

            # VALIDACIÓN CRÍTICA: Orden debe tener items para ciertos estados
            # (MIGRACIÓN DE: operations.fn_validate_order_has_items)
            if new_status.value in ['dispatched', 'delivered', 'returned']:
                if not order.order_items or len(order.order_items) == 0:
                    error_msg = (
                        f"No se puede cambiar orden {order_id} a status '{new_status.value}'. "
                        f"La orden no tiene items."
                    )
                    logger.error(f"❌ {error_msg}")
                    raise ValueError(error_msg)

                logger.info(
                    f"✅ Orden {order_id} tiene {len(order.order_items)} items - OK para status '{new_status.value}'"
                )

            # Actualizar status
            tracking.order_status = new_status.value

            # Agregar notas si hay
            if notes:
                order.notes = (order.notes or "") + f"\n[{new_status.value}] {notes}"

            logger.info(f"📝 Status actualizado: {order_id}, {old_status} → {new_status.value}")

            # PASO 1: Calcular y actualizar costos de delivery/return
            # (MIGRACIÓN DE: operations.fn_calculate_delivery_return_costs)
            DeliveryCostService.calculate_and_update_costs(
                db=db,
                order=order,
                new_status=new_status.value
            )

            # PASO 2: Procesar pago semanal del carrier
            # (MIGRACIÓN DE: operations.fn_update_payment_from_order)
            PaymentService.update_payment_from_order(
                db=db,
                order=order,
                old_status=old_status,
                new_status=new_status.value
            )

            # PASO 3: LÓGICA ESPECIAL según nuevo status (inventario)
            if new_status == OrderStatusEnum.DELIVERED:
                OrderService._handle_delivered_order(db, order)

            elif new_status == OrderStatusEnum.RETURNED:
                OrderService._handle_returned_order(db, order)

            db.commit()

            return tracking

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error actualizando status: {str(e)}")
            raise ValueError(f"Error actualizando status: {str(e)}")

    @staticmethod
    def _handle_delivered_order(db: Session, order: Orders):
        """
        Procesar orden entregada (REDUCIR INVENTARIO)

        Se ejecuta cuando el status cambia a "delivered"
        USA InventoryService (con idempotencia automática)

        VALIDACIÓN CRÍTICA:
        - Verifica stock suficiente ANTES de reducir
        - Si no hay stock, lanza ValueError con detalles
        """

        logger.info(f"📦 Procesando orden entregada: {order.order_id}")

        # PASO 1: VALIDAR STOCK SUFICIENTE para TODOS los items (fail-fast)
        insufficient_items = []
        for item in order.order_items:
            current_stock = InventoryService.get_stock(
                db=db,
                variant_id=item.product_variant_id,
                department=order.customer.department
            )

            if current_stock < item.quantity:
                insufficient_items.append({
                    "product_name": item.product_name,
                    "variant_id": item.product_variant_id,
                    "required": item.quantity,
                    "available": int(current_stock)
                })

        # Si hay items sin stock suficiente, ABORTAR
        if insufficient_items:
            error_msg = "Stock insuficiente para uno o más productos"
            logger.error(f"❌ {error_msg}: {insufficient_items}")
            raise ValueError(
                f"{error_msg}. Detalles: {insufficient_items}"
            )

        # PASO 2: Stock validado OK → Reducir inventario de cada item
        for item in order.order_items:
            InventoryService.reduce_stock_on_delivery(
                db=db,
                variant_id=item.product_variant_id,
                department=order.customer.department,  # Departamento del cliente
                quantity=item.quantity,
                order_id=order.order_id
            )

        logger.info(f"✅ Inventario reducido para orden {order.order_id}")

    @staticmethod
    def _handle_returned_order(db: Session, order: Orders):
        """
        Procesar orden devuelta (AUMENTAR INVENTARIO)

        Se ejecuta cuando el status cambia a "returned"
        USA InventoryService (con idempotencia automática)
        """

        logger.info(f"🔄 Procesando orden devuelta: {order.order_id}")

        # Aumentar inventario de cada item (USA InventoryService)
        for item in order.order_items:
            InventoryService.increase_stock_on_return(
                db=db,
                variant_id=item.product_variant_id,
                department=order.customer.department,
                quantity=item.quantity,
                order_id=order.order_id
            )

        logger.info(f"✅ Inventario restaurado para orden {order.order_id}")

    # ==================== HELPERS ====================

    @staticmethod
    def _find_or_create_customer(db: Session, customer_data) -> Customers:
        """
        Buscar o crear customer

        Busca por phone (único)
        Si no existe, crea nuevo
        """

        # Buscar por phone
        customer = db.query(Customers).filter(
            Customers.phone == customer_data.phone
        ).first()

        if customer:
            # VALIDACIÓN CRÍTICA: Verificar que customer esté activo
            if not customer.is_active:
                error_msg = f"Cliente {customer.customer_id} ({customer.full_name}) está inactivo y no puede realizar órdenes"
                logger.error(f"❌ {error_msg}")
                raise ValueError(error_msg)

            # Actualizar datos si cambiaron
            customer.full_name = customer_data.full_name
            customer.email = customer_data.email
            # Convertir LA_PAZ → LA PAZ (reemplazar _ con espacio)
            customer.department = customer_data.department.replace('_', ' ')
            customer.address = customer_data.address
            customer.reference = customer_data.reference

            db.flush()

            logger.info(f"✅ Customer encontrado y actualizado: {customer.customer_id}")
            return customer

        # Crear nuevo customer
        customer_id = IDGenerator.generate_customer_id(db)

        customer = Customers(
            customer_id=customer_id,
            full_name=customer_data.full_name,
            phone=customer_data.phone,
            email=customer_data.email,
            # Convertir LA_PAZ → LA PAZ (reemplazar _ con espacio)
            department=customer_data.department.replace('_', ' '),
            address=customer_data.address,
            reference=customer_data.reference,
            total_orders=0,
            total_spent_bob=0
        )

        db.add(customer)
        db.flush()

        logger.info(f"✅ Customer creado: {customer_id}")

        return customer

    @staticmethod
    def _update_customer_stats(db: Session, customer_id: str, order_total: float):
        """
        Actualizar estadísticas del customer

        REEMPLAZA: fn_update_customer_stats (trigger)
        """

        customer = db.query(Customers).filter(
            Customers.customer_id == customer_id
        ).first()

        if not customer:
            logger.error(f"❌ Customer no encontrado: {customer_id}")
            return

        customer.total_orders += 1
        customer.total_spent_bob += Decimal(str(order_total))

        db.flush()

        logger.info(f"✅ Customer stats actualizadas: {customer_id}, "
                   f"total_orders={customer.total_orders}, "
                   f"total_spent={customer.total_spent_bob}")

    # ==================== VALIDACIONES ====================

    @staticmethod
    def validate_order_totals(db: Session, order_id: str) -> None:
        """
        Validar que la suma de subtotales de items = total de la orden

        VALIDACIÓN CRÍTICA: Previene errores de cálculo o manipulación

        Lanza ValueError si:
        - La diferencia entre sum(items.subtotal) y order.total > 0.01 BOB

        Args:
            db: Database session
            order_id: ID de la orden a validar

        Raises:
            ValueError: Si los totales no coinciden
        """
        # Obtener orden
        order = db.query(Orders).filter(Orders.order_id == order_id).first()

        if not order:
            raise ValueError(f"Orden no encontrada: {order_id}")

        # Calcular suma de subtotales usando SQL (más eficiente)
        items_total = db.query(
            func.coalesce(func.sum(OrderItems.subtotal), Decimal('0'))
        ).filter(
            OrderItems.order_id == order_id
        ).scalar()

        # Convertir a Decimal para comparación precisa
        items_total = Decimal(str(items_total))
        order_total = Decimal(str(order.total))

        # Calcular diferencia absoluta
        difference = abs(items_total - order_total)

        # Tolerancia de 0.01 BOB para errores de redondeo
        if difference > Decimal('0.01'):
            error_msg = (
                f"ERROR DE VALIDACIÓN: Los totales no coinciden para orden {order_id}. "
                f"Sum(items.subtotal) = {items_total} BOB, "
                f"order.total = {order_total} BOB, "
                f"diferencia = {difference} BOB"
            )
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)

        logger.info(f"✅ Totales validados OK para orden {order_id}: {items_total} BOB")

    @staticmethod
    def validate_no_duplicate_order_24h(
        db: Session,
        customer_id: str,
        items: List
    ) -> None:
        """
        Validar que el cliente NO haya hecho el mismo pedido en las últimas 24 horas

        REGLA ANTI-DUPLICADOS:
        Se bloquea si se cumplen TODAS estas condiciones:
        1. Mismo customer_id
        2. Mismo product_variant_id
        3. Misma quantity
        4. Dentro de las últimas 24 horas

        EJEMPLOS:
        - Cliente compra 2x "Chompa Roja" hoy 10:00
        - Cliente intenta 2x "Chompa Roja" hoy 15:00 → ❌ BLOQUEADO
        - Cliente intenta 3x "Chompa Roja" hoy 15:00 → ✅ PERMITIDO (cantidad diferente)
        - Cliente intenta 2x "Chompa Azul" hoy 15:00 → ✅ PERMITIDO (producto diferente)

        Args:
            db: Database session
            customer_id: ID del cliente
            items: Lista de items de la nueva orden (cada item tiene product_variant_id y quantity)

        Raises:
            ValueError: Si se detecta un pedido duplicado en 24h
        """
        # Calcular timestamp de 24 horas atrás
        time_24h_ago = datetime.now() - timedelta(hours=24)

        # Buscar órdenes del cliente en las últimas 24 horas
        recent_orders = db.query(Orders).filter(
            Orders.customer_id == customer_id,
            Orders.created_at >= time_24h_ago
        ).all()

        if not recent_orders:
            logger.info(f"✅ No hay órdenes recientes para customer {customer_id} en últimas 24h")
            return

        # Para cada item de la nueva orden, verificar si ya fue comprado con misma cantidad
        for new_item in items:
            new_variant_id = new_item.product_variant_id
            new_quantity = new_item.quantity

            # Buscar en órdenes recientes si hay un item con mismo variant_id y quantity
            for recent_order in recent_orders:
                for recent_item in recent_order.order_items:
                    if (recent_item.product_variant_id == new_variant_id and
                        recent_item.quantity == new_quantity):

                        # DUPLICADO DETECTADO
                        hours_ago = (datetime.now() - recent_order.created_at).total_seconds() / 3600

                        error_msg = (
                            f"PEDIDO DUPLICADO DETECTADO: El cliente {customer_id} ya ordenó "
                            f"{new_quantity}x del producto {new_variant_id} "
                            f"hace {hours_ago:.1f} horas (orden {recent_order.order_id}). "
                            f"No se permite el mismo pedido (mismo producto + misma cantidad) en 24 horas."
                        )
                        logger.error(f"❌ {error_msg}")
                        raise ValueError(error_msg)

        logger.info(f"✅ No se detectaron pedidos duplicados para customer {customer_id}")

    # ==================== CONSULTAS ====================

    @staticmethod
    def get_order(db: Session, order_id: str) -> Optional[Orders]:
        """
        Obtener orden por ID con relaciones cargadas (eager loading)

        Carga automáticamente:
        - customer (datos del cliente)
        - order_items (items de la orden)
        - tracking (estado actual)
        - product_variant de cada item
        """
        from sqlalchemy.orm import joinedload

        order = db.query(Orders).filter(
            Orders.order_id == order_id
        ).options(
            joinedload(Orders.customer),
            joinedload(Orders.order_items).joinedload(OrderItems.product_variant),
            joinedload(Orders.tracking)
        ).first()

        return order

    @staticmethod
    def get_customer_orders(db: Session, customer_id: str) -> List[Orders]:
        """
        Obtener todas las órdenes de un cliente
        """
        return db.query(Orders).filter(Orders.customer_id == customer_id).all()

    @staticmethod
    def get_orders_by_status(db: Session, status: str, limit: int = 100) -> List[Orders]:
        """
        Obtener órdenes por estado
        """
        return db.query(Orders).join(OrderTracking).filter(
            OrderTracking.order_status == status
        ).limit(limit).all()

    @staticmethod
    def get_orders_with_filters(
        db: Session,
        status: Optional[str] = None,
        customer_id: Optional[str] = None,
        carrier_id: Optional[str] = None,
        external_order_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[Orders], int]:
        """
        Obtener órdenes con filtros y paginación

        Args:
            db: Database session
            status: Filtrar por estado (new, confirmed, dispatched, delivered, returned, cancelled)
            customer_id: Filtrar por customer_id
            carrier_id: Filtrar por carrier_id
            external_order_id: Filtrar por external_order_id (busca coincidencia parcial)
            date_from: Fecha desde (formato: YYYY-MM-DD)
            date_to: Fecha hasta (formato: YYYY-MM-DD)
            page: Número de página (comienza en 1)
            page_size: Cantidad de órdenes por página

        Returns:
            Tuple (lista_ordenes, total_ordenes)
        """
        from sqlalchemy.orm import joinedload
        from datetime import datetime

        # Construir query base con eager loading
        query = db.query(Orders).options(
            joinedload(Orders.customer),
            joinedload(Orders.tracking)
        )

        # FILTRO 1: Por estado
        if status:
            query = query.join(OrderTracking).filter(OrderTracking.order_status == status)

        # FILTRO 2: Por customer_id
        if customer_id:
            query = query.filter(Orders.customer_id == customer_id)

        # FILTRO 3: Por carrier_id
        if carrier_id:
            query = query.filter(Orders.carrier_id == carrier_id)

        # FILTRO 4: Por external_order_id (coincidencia parcial)
        if external_order_id:
            query = query.filter(Orders.external_order_id.ilike(f"%{external_order_id}%"))

        # FILTRO 5: Por rango de fechas
        if date_from:
            try:
                date_from_dt = datetime.strptime(date_from, "%Y-%m-%d")
                query = query.filter(Orders.created_at >= date_from_dt)
            except ValueError:
                logger.warning(f"Formato de date_from inválido: {date_from}")

        if date_to:
            try:
                date_to_dt = datetime.strptime(date_to, "%Y-%m-%d")
                # Incluir todo el día (hasta las 23:59:59)
                from datetime import timedelta
                date_to_dt = date_to_dt + timedelta(days=1)
                query = query.filter(Orders.created_at < date_to_dt)
            except ValueError:
                logger.warning(f"Formato de date_to inválido: {date_to}")

        # Contar total de órdenes (sin paginación)
        total = query.count()

        # PAGINACIÓN
        offset = (page - 1) * page_size
        query = query.order_by(Orders.created_at.desc())  # Más recientes primero
        query = query.offset(offset).limit(page_size)

        orders = query.all()

        logger.info(
            f"📋 Consulta de órdenes: {len(orders)} de {total} total "
            f"(page={page}, page_size={page_size})"
        )

        return (orders, total)
