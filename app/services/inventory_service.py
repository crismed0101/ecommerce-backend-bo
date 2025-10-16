"""
InventoryService - Gestión de inventario

Responsabilidades:
1. Crear movimientos de inventario (purchase, sale, return, adjustment)
2. Actualizar stock atomicamente
3. Validar stock disponible ANTES de vender
4. IDEMPOTENCY: Evitar duplicar movimientos (check reference_id)

Principios:
- ACID: Transacciones atómicas
- IDEMPOTENCY: Check reference_id antes de crear movimiento
- PESSIMISTIC LOCKING: SELECT FOR UPDATE para evitar race conditions
"""

from sqlalchemy.orm import Session
from sqlalchemy import text, func
from typing import Optional, List
from decimal import Decimal
import logging

from app.models import Inventory, InventoryMovements
from app.services.id_generator import IDGenerator

logger = logging.getLogger(__name__)


class InventoryService:
    """
    Service para gestión de inventario

    TIPOS DE MOVIMIENTOS:
    - purchase: Compra a proveedor (+stock)
    - sale: Venta a cliente (-stock)
    - return: Devolución de cliente (+stock)
    - transfer: Transferencia entre departamentos (+/-)
    - adjustment: Ajuste manual (+/-)
    """

    # ==================== MOVIMIENTOS ====================

    @staticmethod
    def create_movement(
        db: Session,
        variant_id: str,
        department: str,
        movement_type: str,
        quantity: Decimal,
        reference_id: Optional[str] = None
    ) -> Optional[InventoryMovements]:
        """
        Crear movimiento de inventario (IDEMPOTENTE)

        IMPORTANTE:
        - Si reference_id ya existe → NO crear movimiento (idempotencia)
        - Actualiza el stock en inventory automáticamente

        Args:
            db: Database session
            variant_id: ID de la variante
            department: Departamento
            movement_type: Tipo (purchase, sale, return, adjustment)
            quantity: Cantidad (positivo = entrada, negativo = salida)
            reference_id: ID de referencia (order_id, purchase_id, etc.)

        Returns:
            InventoryMovements si se creó, None si ya existía (idempotencia)
        """

        # IDEMPOTENCY CHECK: Si tiene reference_id, verificar que no exista
        if reference_id:
            existing = db.query(InventoryMovements).filter(
                InventoryMovements.reference_id == reference_id,
                InventoryMovements.product_variant_id == variant_id,
                InventoryMovements.department == department
            ).first()

            if existing:
                logger.info(f"🔄 IDEMPOTENCY: Movimiento ya existe para reference_id={reference_id}")
                return None

        # Generar ID
        movement_id = IDGenerator.generate_movement_id(db)

        # Crear movimiento
        movement = InventoryMovements(
            movement_id=movement_id,
            product_variant_id=variant_id,
            department=department,
            movement_type=movement_type,
            quantity=quantity,
            reference_id=reference_id
        )

        db.add(movement)
        db.flush()

        logger.info(f"✅ Movimiento creado: {movement_id} ({movement_type}, qty={quantity})")

        # Actualizar stock
        InventoryService._update_stock(db, variant_id, department, quantity)

        return movement

    @staticmethod
    def _update_stock(
        db: Session,
        variant_id: str,
        department: str,
        quantity_change: Decimal
    ):
        """
        Actualizar stock en inventory (ATOMIC)

        Usa SELECT FOR UPDATE para evitar race conditions
        """

        # PESSIMISTIC LOCK: Bloquear fila hasta commit
        inventory = db.query(Inventory).filter(
            Inventory.product_variant_id == variant_id,
            Inventory.department == department
        ).with_for_update().first()

        if not inventory:
            # Si no existe, crear
            inventory_id = IDGenerator.generate_inventory_id(db)
            inventory = Inventory(
                inventory_id=inventory_id,
                product_variant_id=variant_id,
                department=department,
                stock_quantity=quantity_change
            )
            db.add(inventory)
            logger.info(f"📦 Inventario creado: {variant_id} en {department}, stock={quantity_change}")
        else:
            # Actualizar existente
            old_stock = inventory.stock_quantity
            new_stock = old_stock + quantity_change

            # VALIDACIÓN CRÍTICA: Prevenir stock negativo (DOBLE CAPA DE SEGURIDAD)
            if quantity_change < 0 and new_stock < 0:
                # Es una salida y resultaría en stock negativo
                error_msg = (
                    f"Stock insuficiente para {variant_id} en {department}. "
                    f"Disponible: {old_stock}, Solicitado: {abs(quantity_change)}"
                )
                logger.error(f"❌ {error_msg}")
                raise ValueError(error_msg)

            inventory.stock_quantity = new_stock
            logger.info(f"📦 Stock actualizado: {variant_id} en {department}, "
                       f"{old_stock} → {inventory.stock_quantity}")

        db.flush()

    # ==================== VALIDACIÓN ====================

    @staticmethod
    def validate_stock(
        db: Session,
        variant_id: str,
        department: str,
        quantity_required: Decimal
    ) -> bool:
        """
        Validar si hay stock suficiente

        Returns:
            True si hay stock, False si no
        """

        inventory = db.query(Inventory).filter(
            Inventory.product_variant_id == variant_id,
            Inventory.department == department
        ).first()

        if not inventory:
            logger.warning(f"⚠️ Inventario no existe: {variant_id} en {department}")
            return False

        if inventory.stock_quantity < quantity_required:
            logger.warning(f"⚠️ Stock insuficiente: {variant_id} en {department}, "
                          f"disponible={inventory.stock_quantity}, requerido={quantity_required}")
            return False

        logger.info(f"✅ Stock suficiente: {variant_id} en {department}, "
                   f"disponible={inventory.stock_quantity}")
        return True

    @staticmethod
    def get_stock(
        db: Session,
        variant_id: str,
        department: str
    ) -> Decimal:
        """
        Obtener stock actual

        Returns:
            Stock actual (0 si no existe)
        """

        inventory = db.query(Inventory).filter(
            Inventory.product_variant_id == variant_id,
            Inventory.department == department
        ).first()

        return inventory.stock_quantity if inventory else Decimal(0)

    # ==================== CONSULTAS ====================

    @staticmethod
    def get_movements(
        db: Session,
        variant_id: Optional[str] = None,
        department: Optional[str] = None,
        reference_id: Optional[str] = None,
        limit: int = 100
    ) -> List[InventoryMovements]:
        """
        Obtener movimientos con filtros

        Args:
            variant_id: Filtrar por variante
            department: Filtrar por departamento
            reference_id: Filtrar por referencia
            limit: Límite de resultados
        """

        query = db.query(InventoryMovements)

        if variant_id:
            query = query.filter(InventoryMovements.product_variant_id == variant_id)

        if department:
            query = query.filter(InventoryMovements.department == department)

        if reference_id:
            query = query.filter(InventoryMovements.reference_id == reference_id)

        return query.order_by(InventoryMovements.movement_date.desc()).limit(limit).all()

    @staticmethod
    def get_inventory_by_department(
        db: Session,
        department: str
    ) -> List[Inventory]:
        """
        Obtener todo el inventario de un departamento
        """

        return db.query(Inventory).filter(
            Inventory.department == department
        ).all()

    # ==================== OPERACIONES ESPECIALES ====================

    @staticmethod
    def reduce_stock_on_delivery(
        db: Session,
        variant_id: str,
        department: str,
        quantity: Decimal,
        order_id: str
    ) -> InventoryMovements:
        """
        Reducir stock al entregar orden (IDEMPOTENTE)

        Usado cuando el status de la orden cambia a "delivered"

        Returns:
            InventoryMovements si se creó, None si ya existía
        """

        # quantity debe ser negativo (salida)
        quantity_change = -abs(quantity)

        movement = InventoryService.create_movement(
            db=db,
            variant_id=variant_id,
            department=department,
            movement_type="sale",
            quantity=quantity_change,
            reference_id=order_id
        )

        if movement:
            logger.info(f"✅ Stock reducido por entrega: {order_id}, qty={quantity_change}")
        else:
            logger.info(f"🔄 Stock ya reducido previamente: {order_id}")

        return movement

    @staticmethod
    def increase_stock_on_return(
        db: Session,
        variant_id: str,
        department: str,
        quantity: Decimal,
        order_id: str
    ) -> InventoryMovements:
        """
        Aumentar stock al devolver orden (IDEMPOTENTE)

        Usado cuando el status de la orden cambia a "returned"
        """

        # quantity debe ser positivo (entrada)
        quantity_change = abs(quantity)

        movement = InventoryService.create_movement(
            db=db,
            variant_id=variant_id,
            department=department,
            movement_type="return",
            quantity=quantity_change,
            reference_id=f"{order_id}-return"
        )

        if movement:
            logger.info(f"✅ Stock aumentado por devolución: {order_id}, qty={quantity_change}")
        else:
            logger.info(f"🔄 Stock ya aumentado previamente: {order_id}")

        return movement

    @staticmethod
    def increase_stock_on_purchase(
        db: Session,
        variant_id: str,
        department: str,
        quantity: Decimal,
        purchase_id: str
    ) -> InventoryMovements:
        """
        Aumentar stock al confirmar compra (IDEMPOTENTE)

        Usado cuando se recibe mercancía del proveedor
        """

        # quantity debe ser positivo (entrada)
        quantity_change = abs(quantity)

        movement = InventoryService.create_movement(
            db=db,
            variant_id=variant_id,
            department=department,
            movement_type="purchase",
            quantity=quantity_change,
            reference_id=purchase_id
        )

        if movement:
            logger.info(f"✅ Stock aumentado por compra: {purchase_id}, qty={quantity_change}")
        else:
            logger.info(f"🔄 Stock ya aumentado previamente: {purchase_id}")

        return movement

    # ==================== TRANSFERENCIAS ENTRE DEPARTAMENTOS ====================

    @staticmethod
    def transfer_stock_between_departments(
        db: Session,
        variant_id: str,
        from_department: str,
        to_department: str,
        quantity: Decimal,
        notes: Optional[str] = None
    ) -> tuple[InventoryMovements, InventoryMovements]:
        """
        Transferir stock de un departamento a otro (TRANSACCIÓN ATÓMICA)

        VALIDACIÓN CRÍTICA:
        - Verifica stock suficiente en departamento origen ANTES de transferir
        - Si no hay stock, lanza ValueError

        Args:
            db: Database session
            variant_id: ID de la variante
            from_department: Departamento origen
            to_department: Departamento destino
            quantity: Cantidad a transferir
            notes: Notas opcionales sobre la transferencia

        Returns:
            Tuple (movement_salida, movement_entrada)

        Raises:
            ValueError: Si no hay stock suficiente en origen
        """
        try:
            # PASO 1: VALIDAR STOCK SUFICIENTE en origen
            current_stock = InventoryService.get_stock(db, variant_id, from_department)

            if current_stock < quantity:
                error_msg = (
                    f"Stock insuficiente para transferir de {from_department} a {to_department}. "
                    f"Disponible: {current_stock}, Solicitado: {quantity}"
                )
                logger.error(f"❌ {error_msg}")
                raise ValueError(error_msg)

            # PASO 2: Generar reference_id único para la transferencia
            transfer_id = IDGenerator.generate_movement_id(db)

            # PASO 3: SALIDA del departamento origen
            movement_out = InventoryService.create_movement(
                db=db,
                variant_id=variant_id,
                department=from_department,
                movement_type="transfer_out",
                quantity=-abs(quantity),  # Negativo (salida)
                reference_id=f"TRANSFER-{transfer_id}"
            )

            # PASO 4: ENTRADA al departamento destino
            movement_in = InventoryService.create_movement(
                db=db,
                variant_id=variant_id,
                department=to_department,
                movement_type="transfer_in",
                quantity=abs(quantity),  # Positivo (entrada)
                reference_id=f"TRANSFER-{transfer_id}"
            )

            logger.info(
                f"✅ Transferencia completada: {quantity} unidades de {variant_id} "
                f"desde {from_department} → {to_department} (ref: TRANSFER-{transfer_id})"
            )

            db.flush()
            return (movement_out, movement_in)

        except Exception as e:
            logger.error(f"❌ Error en transferencia: {str(e)}")
            raise ValueError(f"Error en transferencia: {str(e)}")

    # ==================== ALERTAS DE STOCK BAJO ====================

    @staticmethod
    def check_low_stock_alerts(
        db: Session,
        department: Optional[str] = None
    ) -> List[dict]:
        """
        Verificar productos con stock bajo

        Retorna lista de productos donde stock_quantity < min_stock_quantity

        Args:
            db: Database session
            department: Filtrar por departamento (None = todos)

        Returns:
            Lista de dicts con info de productos con stock bajo
        """
        from app.models import ProductVariants

        query = db.query(Inventory).join(
            ProductVariants,
            ProductVariants.product_variant_id == Inventory.product_variant_id
        ).filter(
            Inventory.stock_quantity < Inventory.min_stock_quantity
        )

        if department:
            query = query.filter(Inventory.department == department)

        low_stock_items = query.all()

        alerts = []
        for item in low_stock_items:
            alerts.append({
                'variant_id': item.product_variant_id,
                'variant_name': item.product_variant.variant_name if item.product_variant else 'N/A',
                'department': item.department,
                'current_stock': float(item.stock_quantity),
                'min_stock': float(item.min_stock_quantity),
                'deficit': float(item.min_stock_quantity - item.stock_quantity),
                'alert_level': 'CRITICAL' if item.stock_quantity == 0 else 'WARNING'
            })

        if alerts:
            logger.warning(f"⚠️ {len(alerts)} productos con stock bajo detectados")
        else:
            logger.info(f"✅ No hay alertas de stock bajo")

        return alerts

    # ==================== AJUSTES CON AUDITORÍA ====================

    @staticmethod
    def create_adjustment_with_audit(
        db: Session,
        variant_id: str,
        department: str,
        quantity_change: Decimal,
        reason: str,
        responsible_user: str,
        notes: Optional[str] = None
    ) -> InventoryMovements:
        """
        Crear ajuste de inventario con auditoría completa

        AUDITORÍA:
        - Registra quién hizo el ajuste (responsible_user)
        - Registra por qué (reason)
        - Registra cuándo (automático)
        - Registra notas adicionales

        Args:
            db: Database session
            variant_id: ID de la variante
            department: Departamento
            quantity_change: Cambio en cantidad (positivo=entrada, negativo=salida)
            reason: Razón del ajuste (ej: "Inventario físico", "Producto dañado", "Error de sistema")
            responsible_user: Usuario que autoriza el ajuste
            notes: Notas adicionales

        Returns:
            InventoryMovements creado
        """
        try:
            # Generar reference_id único
            adjustment_id = IDGenerator.generate_movement_id(db)

            # Crear descripción completa para auditoría
            audit_description = f"AJUSTE: {reason} | Usuario: {responsible_user}"
            if notes:
                audit_description += f" | Notas: {notes}"

            # Crear movimiento de ajuste
            movement = InventoryService.create_movement(
                db=db,
                variant_id=variant_id,
                department=department,
                movement_type="adjustment",
                quantity=quantity_change,
                reference_id=f"ADJ-{adjustment_id}"
            )

            # Aquí podrías agregar un registro adicional en una tabla de auditoría
            # Por ahora, lo registramos en logs
            logger.info(
                f"📝 AJUSTE AUDITADO: {variant_id} en {department}, "
                f"qty_change={quantity_change}, razón='{reason}', "
                f"responsable={responsible_user}"
            )

            db.flush()
            return movement

        except Exception as e:
            logger.error(f"❌ Error creando ajuste con auditoría: {str(e)}")
            raise ValueError(f"Error creando ajuste: {str(e)}")

    # ==================== REPORTES DE ROTACIÓN ====================

    @staticmethod
    def calculate_inventory_turnover(
        db: Session,
        variant_id: str,
        department: str,
        days_period: int = 30
    ) -> dict:
        """
        Calcular tasa de rotación de inventario (Inventory Turnover Rate)

        FÓRMULA:
        Turnover Rate = Total Sales in Period / Average Inventory

        Args:
            db: Database session
            variant_id: ID de la variante
            department: Departamento
            days_period: Período en días (default: 30)

        Returns:
            Dict con métricas de rotación
        """
        from datetime import datetime, timedelta

        date_from = datetime.now() - timedelta(days=days_period)

        # PASO 1: Calcular total de ventas en el período
        total_sales = db.query(
            func.coalesce(func.sum(func.abs(InventoryMovements.quantity)), Decimal('0'))
        ).filter(
            InventoryMovements.product_variant_id == variant_id,
            InventoryMovements.department == department,
            InventoryMovements.movement_type == "sale",
            InventoryMovements.movement_date >= date_from
        ).scalar()

        # PASO 2: Calcular inventario promedio
        # Simplificación: usar stock actual (en un sistema real, calcular promedio histórico)
        current_stock = InventoryService.get_stock(db, variant_id, department)

        # PASO 3: Calcular turnover rate
        if current_stock > 0:
            turnover_rate = float(total_sales) / float(current_stock)
            days_to_sell_out = days_period / turnover_rate if turnover_rate > 0 else float('inf')
        else:
            turnover_rate = 0
            days_to_sell_out = 0

        result = {
            'variant_id': variant_id,
            'department': department,
            'period_days': days_period,
            'total_sales': float(total_sales),
            'current_stock': float(current_stock),
            'turnover_rate': round(turnover_rate, 2),
            'days_to_sell_out': round(days_to_sell_out, 1) if days_to_sell_out != float('inf') else None,
            'velocity': 'HIGH' if turnover_rate > 2 else ('MEDIUM' if turnover_rate > 0.5 else 'LOW')
        }

        logger.info(
            f"📊 Turnover calculado: {variant_id} en {department}, "
            f"rate={result['turnover_rate']}x, velocity={result['velocity']}"
        )

        return result

    # ==================== VALORIZACIÓN FIFO/LIFO ====================

    @staticmethod
    def calculate_inventory_value_fifo(
        db: Session,
        variant_id: Optional[str] = None,
        department: Optional[str] = None
    ) -> dict:
        """
        Calcular valor total de inventario usando método FIFO

        FIFO = First In, First Out
        - Asume que los primeros productos comprados son los primeros vendidos
        - El inventario restante se valora a los costos más recientes

        Args:
            db: Database session
            variant_id: Filtrar por variante (None = todas)
            department: Filtrar por departamento (None = todos)

        Returns:
            Dict con valorización FIFO
        """
        from app.models import Purchases, PurchaseItems

        # PASO 1: Obtener inventario actual
        query = db.query(Inventory)

        if variant_id:
            query = query.filter(Inventory.product_variant_id == variant_id)
        if department:
            query = query.filter(Inventory.department == department)

        inventory_items = query.all()

        total_value = Decimal('0')
        total_units = Decimal('0')

        # PASO 2: Para cada item de inventario, calcular valor usando FIFO
        for inv_item in inventory_items:
            # Obtener compras más recientes de este producto (FIFO = últimas compras)
            recent_purchases = db.query(PurchaseItems).join(
                Purchases
            ).filter(
                PurchaseItems.product_variant_id == inv_item.product_variant_id
            ).order_by(
                Purchases.purchase_date.desc()
            ).limit(10).all()

            if recent_purchases:
                # Usar precio de compra más reciente
                latest_cost = recent_purchases[0].unit_price
            else:
                # Si no hay compras, usar 0
                latest_cost = Decimal('0')

            item_value = inv_item.stock_quantity * latest_cost
            total_value += item_value
            total_units += inv_item.stock_quantity

        result = {
            'method': 'FIFO',
            'total_inventory_value': float(total_value),
            'total_units': float(total_units),
            'average_cost_per_unit': float(total_value / total_units) if total_units > 0 else 0,
            'currency': 'BOB',
            'items_count': len(inventory_items)
        }

        logger.info(
            f"💰 Valorización FIFO: {result['total_inventory_value']} BOB "
            f"({result['total_units']} unidades)"
        )

        return result

    @staticmethod
    def calculate_inventory_value_lifo(
        db: Session,
        variant_id: Optional[str] = None,
        department: Optional[str] = None
    ) -> dict:
        """
        Calcular valor total de inventario usando método LIFO

        LIFO = Last In, First Out
        - Asume que los últimos productos comprados son los primeros vendidos
        - El inventario restante se valora a los costos más antiguos

        Args:
            db: Database session
            variant_id: Filtrar por variante (None = todas)
            department: Filtrar por departamento (None = todos)

        Returns:
            Dict con valorización LIFO
        """
        from app.models import Purchases, PurchaseItems

        # PASO 1: Obtener inventario actual
        query = db.query(Inventory)

        if variant_id:
            query = query.filter(Inventory.product_variant_id == variant_id)
        if department:
            query = query.filter(Inventory.department == department)

        inventory_items = query.all()

        total_value = Decimal('0')
        total_units = Decimal('0')

        # PASO 2: Para cada item de inventario, calcular valor usando LIFO
        for inv_item in inventory_items:
            # Obtener compras más antiguas de este producto (LIFO = primeras compras)
            oldest_purchases = db.query(PurchaseItems).join(
                Purchases
            ).filter(
                PurchaseItems.product_variant_id == inv_item.product_variant_id
            ).order_by(
                Purchases.purchase_date.asc()
            ).limit(10).all()

            if oldest_purchases:
                # Usar precio de compra más antiguo
                oldest_cost = oldest_purchases[0].unit_price
            else:
                # Si no hay compras, usar 0
                oldest_cost = Decimal('0')

            item_value = inv_item.stock_quantity * oldest_cost
            total_value += item_value
            total_units += inv_item.stock_quantity

        result = {
            'method': 'LIFO',
            'total_inventory_value': float(total_value),
            'total_units': float(total_units),
            'average_cost_per_unit': float(total_value / total_units) if total_units > 0 else 0,
            'currency': 'BOB',
            'items_count': len(inventory_items)
        }

        logger.info(
            f"💰 Valorización LIFO: {result['total_inventory_value']} BOB "
            f"({result['total_units']} unidades)"
        )

        return result
