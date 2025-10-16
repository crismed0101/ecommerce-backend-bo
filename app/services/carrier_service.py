"""
CarrierService - Gestión de carriers (transportistas)

Responsabilidades:
1. Validar desactivación de carrier (sin órdenes ni pagos pendientes)
2. Consultar carriers activos/inactivos
3. Gestionar carrier_rates

Principios:
- VALIDATION: Validaciones críticas antes de desactivar
- DATA INTEGRITY: Garantizar consistencia antes de cambios importantes

REEMPLAZA:
- operations.fn_validate_carrier_deactivation() (trigger BEFORE UPDATE on carriers)
"""

from sqlalchemy.orm import Session
from typing import Optional, List
import logging

from app.models import Carriers, Orders, OrderTracking, Payments

logger = logging.getLogger(__name__)


class CarrierService:
    """
    Service para gestión de carriers

    LÓGICA ORIGINAL (PostgreSQL trigger):
    - Se ejecuta ANTES de UPDATE en carriers
    - Solo valida cuando is_active cambia de true → false
    - Verifica que no haya:
        1. Órdenes pendientes (status NOT IN delivered, returned, cancelled)
        2. Pagos pendientes (payment_status = 'pending')
    - Si hay pendientes, lanza excepción
    """

    # ==================== VALIDACIONES ====================

    @staticmethod
    def validate_deactivation(
        db: Session,
        carrier_id: str
    ) -> tuple[bool, Optional[str]]:
        """
        Validar si un carrier puede ser desactivado

        Verifica:
        1. No tenga órdenes pendientes (no delivered, no returned, no cancelled)
        2. No tenga pagos pendientes (payment_status = 'pending')

        Args:
            db: Database session
            carrier_id: ID del carrier a validar

        Returns:
            Tuple (puede_desactivar: bool, mensaje_error: Optional[str])

        Raises:
            ValueError: Si hay órdenes o pagos pendientes
        """

        # PASO 1: Verificar órdenes pendientes
        pending_orders_count = db.query(Orders).join(OrderTracking).filter(
            Orders.carrier_id == carrier_id,
            OrderTracking.order_status.notin_(['delivered', 'returned', 'cancelled'])
        ).count()

        if pending_orders_count > 0:
            error_msg = (
                f"No se puede desactivar carrier {carrier_id}. "
                f"Tiene {pending_orders_count} órdenes pendientes."
            )
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)

        # PASO 2: Verificar pagos pendientes
        pending_payments_count = db.query(Payments).filter(
            Payments.carrier_id == carrier_id,
            Payments.payment_status == 'pending'
        ).count()

        if pending_payments_count > 0:
            error_msg = (
                f"No se puede desactivar carrier {carrier_id}. "
                f"Tiene {pending_payments_count} pagos pendientes."
            )
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)

        logger.info(
            f"✅ Carrier {carrier_id} puede desactivarse correctamente. "
            f"Sin operaciones pendientes."
        )

        return (True, None)

    @staticmethod
    def deactivate_carrier(
        db: Session,
        carrier_id: str
    ) -> Carriers:
        """
        Desactivar un carrier (cambia is_active a False)

        Valida automáticamente antes de desactivar

        Args:
            db: Database session
            carrier_id: ID del carrier

        Returns:
            Carrier desactivado

        Raises:
            ValueError: Si no existe o tiene operaciones pendientes
        """

        # Buscar carrier
        carrier = db.query(Carriers).filter(
            Carriers.carrier_id == carrier_id
        ).first()

        if not carrier:
            raise ValueError(f"Carrier no encontrado: {carrier_id}")

        if not carrier.is_active:
            logger.info(f"⚠️ Carrier {carrier_id} ya estaba inactivo")
            return carrier

        # Validar antes de desactivar
        CarrierService.validate_deactivation(db, carrier_id)

        # Desactivar
        carrier.is_active = False
        db.flush()

        logger.info(f"✅ Carrier {carrier_id} desactivado exitosamente")

        return carrier

    @staticmethod
    def activate_carrier(
        db: Session,
        carrier_id: str
    ) -> Carriers:
        """
        Activar un carrier (cambia is_active a True)

        Args:
            db: Database session
            carrier_id: ID del carrier

        Returns:
            Carrier activado

        Raises:
            ValueError: Si no existe
        """

        # Buscar carrier
        carrier = db.query(Carriers).filter(
            Carriers.carrier_id == carrier_id
        ).first()

        if not carrier:
            raise ValueError(f"Carrier no encontrado: {carrier_id}")

        if carrier.is_active:
            logger.info(f"⚠️ Carrier {carrier_id} ya estaba activo")
            return carrier

        # Activar
        carrier.is_active = True
        db.flush()

        logger.info(f"✅ Carrier {carrier_id} activado exitosamente")

        return carrier

    # ==================== CONSULTAS ====================

    @staticmethod
    def get_carrier(
        db: Session,
        carrier_id: str
    ) -> Optional[Carriers]:
        """
        Obtener carrier por ID

        Args:
            db: Database session
            carrier_id: ID del carrier

        Returns:
            Carrier si existe, None si no
        """

        return db.query(Carriers).filter(
            Carriers.carrier_id == carrier_id
        ).first()

    @staticmethod
    def get_active_carriers(
        db: Session
    ) -> List[Carriers]:
        """
        Obtener todos los carriers activos

        Args:
            db: Database session

        Returns:
            Lista de carriers activos
        """

        return db.query(Carriers).filter(
            Carriers.is_active == True
        ).all()

    @staticmethod
    def get_all_carriers(
        db: Session,
        include_inactive: bool = True
    ) -> List[Carriers]:
        """
        Obtener todos los carriers

        Args:
            db: Database session
            include_inactive: Si incluir carriers inactivos

        Returns:
            Lista de carriers
        """

        query = db.query(Carriers)

        if not include_inactive:
            query = query.filter(Carriers.is_active == True)

        return query.all()
