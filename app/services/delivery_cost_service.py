"""
DeliveryCostService - Cálculo de costos de entrega y devolución

Responsabilidades:
1. Calcular delivery_cost según carrier_rates y tipo de envío (normal/express)
2. Calcular return_cost según carrier_rates
3. Actualizar orden con costos calculados

Principios:
- SEPARATION OF CONCERNS: Solo calcula costos, no gestiona inventario ni pagos
- DATABASE LOOKUP: Busca tarifas en carrier_rates
- CONDITIONAL LOGIC: Aplica comisión express o normal según is_priority_shipping

REEMPLAZA:
- operations.fn_calculate_delivery_return_costs() (trigger AFTER UPDATE on order_tracking)
"""

from sqlalchemy.orm import Session
from decimal import Decimal
from typing import Tuple, Optional
import logging

from app.models import Orders, Carriers, CarrierRates

logger = logging.getLogger(__name__)


class DeliveryCostService:
    """
    Service para calcular costos de entrega y devolución

    LÓGICA ORIGINAL (PostgreSQL trigger):
    - Se ejecuta DESPUÉS de cambiar order_tracking.order_status
    - Busca comisiones en carrier_rates (commission_delivery, commission_return, commission_express)
    - Si status = 'delivered':
        - is_priority = true → usa commission_express
        - is_priority = false → usa commission_delivery
    - Si status = 'returned':
        - usa commission_return
    - Actualiza orders con delivery_cost, return_cost, priority_shipping_cost
    """

    # ==================== CALCULAR COSTOS ====================

    @staticmethod
    def calculate_and_update_costs(
        db: Session,
        order: Orders,
        new_status: str
    ) -> Tuple[Decimal, Decimal]:
        """
        Calcular y actualizar costos de entrega/devolución según estado de orden

        Args:
            db: Database session
            order: Orden a actualizar (debe tener customer y carrier_id)
            new_status: Nuevo estado de la orden ('delivered', 'returned', etc.)

        Returns:
            Tuple[delivery_cost, return_cost]

        Raises:
            ValueError: Si no se encuentra carrier_rates para el carrier y departamento
        """

        # PASO 1: Validar que la orden tenga carrier asignado
        if not order.carrier_id:
            logger.info(f"📦 Orden {order.order_id} sin carrier asignado. Costos = 0")

            # Actualizar orden con costos = 0
            order.delivery_cost = Decimal('0')
            order.return_cost = Decimal('0')
            order.priority_shipping_cost = Decimal('0')

            db.flush()

            return (Decimal('0'), Decimal('0'))

        # PASO 2: Buscar comisiones del carrier para el departamento del cliente
        carrier_rate = db.query(CarrierRates).filter(
            CarrierRates.carrier_id == order.carrier_id,
            CarrierRates.department == order.customer.department
        ).first()

        if not carrier_rate:
            # CASO EDGE: No hay tarifas configuradas para este carrier+departamento
            logger.warning(
                f"⚠️ No se encontraron tarifas para carrier {order.carrier_id} "
                f"en departamento {order.customer.department}. Usando costos = 0"
            )

            # Actualizar orden con costos = 0
            order.delivery_cost = Decimal('0')
            order.return_cost = Decimal('0')
            order.priority_shipping_cost = Decimal('0')

            db.flush()

            return (Decimal('0'), Decimal('0'))

        # PASO 3: Calcular costos según el nuevo estado
        delivery_cost = Decimal('0')
        return_cost = Decimal('0')

        if new_status == 'delivered':
            # LÓGICA CRÍTICA: Distinguir entre envío express y normal
            if order.is_priority_shipping:
                delivery_cost = carrier_rate.commission_express
                logger.info(
                    f"📦 Orden {order.order_id} - Envío EXPRESS: {delivery_cost} BOB "
                    f"(carrier={order.carrier_id}, dept={order.customer.department})"
                )
            else:
                delivery_cost = carrier_rate.commission_delivery
                logger.info(
                    f"📦 Orden {order.order_id} - Envío NORMAL: {delivery_cost} BOB "
                    f"(carrier={order.carrier_id}, dept={order.customer.department})"
                )

            return_cost = Decimal('0')

        elif new_status == 'returned':
            # Orden devuelta: solo costo de devolución
            delivery_cost = Decimal('0')
            return_cost = carrier_rate.commission_return

            logger.info(
                f"🔄 Orden {order.order_id} - DEVOLUCION: {return_cost} BOB "
                f"(carrier={order.carrier_id}, dept={order.customer.department})"
            )

        else:
            # Otros estados (new, confirmed, dispatched, cancelled): sin costos
            delivery_cost = Decimal('0')
            return_cost = Decimal('0')

            logger.info(
                f"📦 Orden {order.order_id} - Estado '{new_status}': sin costos de carrier"
            )

        # PASO 4: Actualizar orden con costos calculados
        order.delivery_cost = delivery_cost
        order.return_cost = return_cost

        # priority_shipping_cost solo se llena si es envío prioritario
        if order.is_priority_shipping and new_status == 'delivered':
            order.priority_shipping_cost = delivery_cost
        else:
            order.priority_shipping_cost = Decimal('0')

        db.flush()

        logger.info(
            f"✅ Costos actualizados para orden {order.order_id}: "
            f"delivery={delivery_cost}, return={return_cost}, "
            f"priority={order.priority_shipping_cost}"
        )

        return (delivery_cost, return_cost)

    # ==================== CONSULTAS ====================

    @staticmethod
    def get_carrier_rates(
        db: Session,
        carrier_id: str,
        department: str
    ) -> Optional[CarrierRates]:
        """
        Obtener tarifas de un carrier para un departamento específico

        Args:
            db: Database session
            carrier_id: ID del carrier
            department: Departamento (LA PAZ, SANTA CRUZ, etc.)

        Returns:
            CarrierRates si existe, None si no
        """

        return db.query(CarrierRates).filter(
            CarrierRates.carrier_id == carrier_id,
            CarrierRates.department == department
        ).first()

    @staticmethod
    def validate_carrier_active(
        db: Session,
        carrier_id: str
    ) -> bool:
        """
        Validar que un carrier esté activo

        Args:
            db: Database session
            carrier_id: ID del carrier

        Returns:
            True si está activo, False si no existe o está inactivo
        """

        carrier = db.query(Carriers).filter(
            Carriers.carrier_id == carrier_id
        ).first()

        if not carrier:
            logger.warning(f"⚠️ Carrier {carrier_id} no encontrado")
            return False

        if not carrier.is_active:
            logger.warning(f"⚠️ Carrier {carrier_id} está INACTIVO")
            return False

        return True
