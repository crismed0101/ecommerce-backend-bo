"""
PaymentService - Gestión de pagos semanales a carriers

Responsabilidades:
1. Crear/actualizar pagos semanales por carrier
2. Agregar órdenes a pagos (payment_orders)
3. Calcular balances anteriores (arrastre de saldo negativo)
4. Revertir pagos si el estado de orden cambia
5. Validar carrier activo antes de procesar pagos

Principios:
- WEEKLY AGGREGATION: Agrupa pagos por semana (week_start_date)
- BALANCE CARRYOVER: Arrastra saldo negativo de semana anterior
- IDEMPOTENCY: Verifica estados previos antes de procesar
- ATOMIC OPERATIONS: Todo en una sola transacción

REEMPLAZA:
- operations.fn_update_payment_from_order() (trigger AFTER UPDATE on order_tracking)
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional, Tuple
import logging

from app.models import Orders, Carriers, Payments, PaymentOrders, FinancialTransactions
from app.services.id_generator import IDGenerator

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Service para gestionar pagos semanales a carriers

    LÓGICA ORIGINAL (PostgreSQL trigger):
    - Se ejecuta DESPUÉS de cambiar order_tracking.order_status
    - Valida que carrier.is_active = true
    - Calcula "deltas" (cambios) según OLD y NEW status:
        - Si OLD = 'delivered' → revertir contribución anterior
        - Si NEW = 'delivered' → añadir nueva contribución
        - Si OLD = 'returned' → revertir devolución anterior
        - Si NEW = 'returned' → añadir nueva devolución
    - Busca/crea payment para la semana del carrier
    - Actualiza totales: deliveries, returns, net_amount, final_amount
    - Mantiene tabla payment_orders (qué orden contribuyó con cuánto)
    - Calcula balance anterior (saldo negativo de semana anterior)
    """

    # ==================== PROCESAR PAGO DESDE ORDEN ====================

    @staticmethod
    def update_payment_from_order(
        db: Session,
        order: Orders,
        old_status: str,
        new_status: str
    ) -> Optional[Payments]:
        """
        Actualizar pago semanal cuando cambia el estado de una orden

        Args:
            db: Database session
            order: Orden que cambió de estado (debe tener customer, carrier_id, costs)
            old_status: Estado anterior de la orden
            new_status: Nuevo estado de la orden

        Returns:
            Payment actualizado/creado, o None si no se procesó pago

        Raises:
            ValueError: Si hay inconsistencias en los datos
        """

        # PASO 0: Validar que la orden tenga carrier
        if not order.carrier_id:
            logger.info(f"💳 Orden {order.order_id} sin carrier. No se procesará pago")
            return None

        # PASO 1: VALIDACIÓN CRÍTICA - Carrier debe estar activo
        carrier = db.query(Carriers).filter(
            Carriers.carrier_id == order.carrier_id
        ).first()

        if not carrier:
            logger.warning(f"⚠️ Carrier {order.carrier_id} no encontrado")
            return None

        if not carrier.is_active:
            logger.warning(
                f"⚠️ Carrier {order.carrier_id} está INACTIVO. "
                f"No se procesará pago para orden {order.order_id}"
            )
            return None

        # PASO 2: Calcular deltas (cambios en contribuciones)
        delta_deliveries = 0
        delta_deliveries_amount = Decimal('0')
        delta_returns = 0
        delta_returns_amount = Decimal('0')

        # Revertir estado anterior si era 'delivered'
        if old_status == 'delivered':
            delta_deliveries -= 1
            # Contribución: total de la orden MENOS el costo de entrega (lo que le queda al carrier)
            delta_deliveries_amount -= (order.total - order.delivery_cost)

            # Eliminar payment_order anterior (para evitar duplicados)
            db.query(PaymentOrders).filter(
                PaymentOrders.order_id == order.order_id,
                PaymentOrders.contribution_type == 'delivery'
            ).delete(synchronize_session=False)

            logger.info(
                f"🔄 Revirtiendo contribución anterior de orden {order.order_id}: "
                f"-{order.total - order.delivery_cost} BOB"
            )

        # Agregar nuevo estado si es 'delivered'
        if new_status == 'delivered':
            delta_deliveries += 1
            delta_deliveries_amount += (order.total - order.delivery_cost)

        # Revertir estado anterior si era 'returned'
        if old_status == 'returned':
            delta_returns -= 1
            delta_returns_amount -= order.return_cost

            # Eliminar payment_order anterior
            db.query(PaymentOrders).filter(
                PaymentOrders.order_id == order.order_id,
                PaymentOrders.contribution_type == 'return'
            ).delete(synchronize_session=False)

            logger.info(
                f"🔄 Revirtiendo devolución anterior de orden {order.order_id}: "
                f"-{order.return_cost} BOB"
            )

        # Agregar nuevo estado si es 'returned'
        if new_status == 'returned':
            delta_returns += 1
            delta_returns_amount += order.return_cost

        # PASO 3: Si no hay cambios, no procesar
        if delta_deliveries == 0 and delta_returns == 0:
            logger.info(
                f"💳 Sin cambios de pago para orden {order.order_id} "
                f"(transición: {old_status} → {new_status})"
            )
            return None

        logger.info(
            f"💳 Procesando cambio de pago para orden {order.order_id}: "
            f"deliveries delta={delta_deliveries} ({delta_deliveries_amount} BOB), "
            f"returns delta={delta_returns} ({delta_returns_amount} BOB)"
        )

        # PASO 4: Calcular fechas de la semana (lunes a domingo)
        # Usar la fecha de actualización del tracking (now)
        week_start = PaymentService._get_week_start(datetime.now())
        week_end = week_start + timedelta(days=6)

        # PASO 5: Buscar o crear payment para esta semana
        payment = PaymentService._find_or_create_payment(
            db=db,
            carrier_id=order.carrier_id,
            week_start=week_start,
            week_end=week_end
        )

        # PASO 6: Actualizar totales del payment
        payment.total_deliveries += delta_deliveries
        payment.total_deliveries_amount += delta_deliveries_amount
        payment.total_returns += delta_returns
        payment.total_returns_amount += delta_returns_amount

        # Calcular net_amount y final_amount
        payment.total_net_amount = (
            payment.total_deliveries_amount - payment.total_returns_amount
        )
        payment.total_final_amount = (
            payment.total_net_amount + payment.previous_balance
        )

        db.flush()

        logger.info(
            f"✅ Payment {payment.payment_id} actualizado: "
            f"deliveries={payment.total_deliveries} ({payment.total_deliveries_amount} BOB), "
            f"returns={payment.total_returns} ({payment.total_returns_amount} BOB), "
            f"net={payment.total_net_amount} BOB, final={payment.total_final_amount} BOB"
        )

        # PASO 7: Crear payment_order si es delivery o return
        if new_status == 'delivered':
            PaymentService._create_payment_order(
                db=db,
                payment_id=payment.payment_id,
                order_id=order.order_id,
                contribution_type='delivery',
                amount_contributed=order.total - order.delivery_cost,
                order_total=order.total,
                commission_applied=order.delivery_cost
            )

        elif new_status == 'returned':
            PaymentService._create_payment_order(
                db=db,
                payment_id=payment.payment_id,
                order_id=order.order_id,
                contribution_type='return',
                amount_contributed=order.return_cost,
                order_total=order.total,
                commission_applied=order.return_cost
            )

        # PASO 8: Limpiar payment si quedó vacío (todas las órdenes revertidas)
        if payment.total_deliveries <= 0 and payment.total_returns <= 0:
            logger.warning(
                f"⚠️ Payment {payment.payment_id} quedó vacío (sin órdenes). Eliminando..."
            )
            db.delete(payment)
            db.flush()
            return None

        return payment

    # ==================== HELPERS ====================

    @staticmethod
    def _get_week_start(date: datetime) -> datetime:
        """
        Obtener el lunes de la semana de una fecha (inicio de semana)

        Args:
            date: Fecha de referencia

        Returns:
            Fecha del lunes (00:00:00) de esa semana
        """
        # weekday(): 0=Monday, 6=Sunday
        days_since_monday = date.weekday()
        week_start = date - timedelta(days=days_since_monday)

        # Setear a medianoche (00:00:00)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        return week_start

    @staticmethod
    def _find_or_create_payment(
        db: Session,
        carrier_id: str,
        week_start: datetime,
        week_end: datetime
    ) -> Payments:
        """
        Buscar o crear payment para un carrier en una semana específica

        Si no existe, calcula el balance anterior (saldo negativo de semana anterior)

        Args:
            db: Database session
            carrier_id: ID del carrier
            week_start: Inicio de la semana (lunes)
            week_end: Fin de la semana (domingo)

        Returns:
            Payment existente o nuevo
        """

        # Buscar payment existente
        payment = db.query(Payments).filter(
            Payments.carrier_id == carrier_id,
            Payments.week_start_date == week_start.date()
        ).first()

        if payment:
            logger.info(f"💳 Payment existente encontrado: {payment.payment_id}")
            return payment

        # No existe → crear nuevo
        payment_id = IDGenerator.generate_payment_id(db)

        # CALCULAR BALANCE ANTERIOR
        # Buscar el payment de la semana anterior
        previous_payment = db.query(Payments).filter(
            Payments.carrier_id == carrier_id,
            Payments.week_start_date < week_start.date()
        ).order_by(Payments.week_start_date.desc()).first()

        previous_balance = Decimal('0')

        if previous_payment and previous_payment.total_final_amount < 0:
            # Si la semana anterior quedó con saldo negativo, arrastrarlo
            previous_balance = previous_payment.total_final_amount
            logger.info(
                f"💳 Arrastrando balance anterior: {previous_balance} BOB "
                f"(de payment {previous_payment.payment_id})"
            )

        # Crear nuevo payment
        payment = Payments(
            payment_id=payment_id,
            carrier_id=carrier_id,
            week_start_date=week_start.date(),
            week_end_date=week_end.date(),
            total_deliveries=0,
            total_deliveries_amount=Decimal('0'),
            total_returns=0,
            total_returns_amount=Decimal('0'),
            total_net_amount=Decimal('0'),
            previous_balance=previous_balance,
            total_final_amount=previous_balance,
            payment_status='pending'
        )

        db.add(payment)
        db.flush()

        logger.info(
            f"✅ Payment creado: {payment_id} "
            f"(carrier={carrier_id}, semana={week_start.date()} - {week_end.date()}, "
            f"balance_anterior={previous_balance})"
        )

        return payment

    @staticmethod
    def _create_payment_order(
        db: Session,
        payment_id: str,
        order_id: str,
        contribution_type: str,
        amount_contributed: Decimal,
        order_total: Decimal,
        commission_applied: Decimal
    ) -> PaymentOrders:
        """
        Crear registro en payment_orders (tracking de qué orden contribuyó con cuánto)

        Args:
            db: Database session
            payment_id: ID del payment
            order_id: ID de la orden
            contribution_type: 'delivery' o 'return'
            amount_contributed: Cantidad que contribuye al pago
            order_total: Total de la orden
            commission_applied: Comisión aplicada

        Returns:
            PaymentOrders creado
        """

        payment_order_id = IDGenerator.generate_payment_order_id(db)

        payment_order = PaymentOrders(
            payment_order_id=payment_order_id,
            payment_id=payment_id,
            order_id=order_id,
            contribution_type=contribution_type,
            amount_contributed=amount_contributed,
            order_total=order_total,
            commission_applied=commission_applied
        )

        db.add(payment_order)
        db.flush()

        logger.info(
            f"✅ PaymentOrder creado: {payment_order_id} "
            f"(payment={payment_id}, order={order_id}, type={contribution_type}, "
            f"amount={amount_contributed} BOB)"
        )

        return payment_order

    # ==================== TRANSACCIONES FINANCIERAS ====================

    @staticmethod
    def create_transaction_from_payment(
        db: Session,
        payment: Payments,
        old_status: str
    ) -> Optional[FinancialTransactions]:
        """
        Crear transacción financiera cuando un payment se marca como "paid"

        (MIGRACIÓN DE: operations.fn_create_transaction_from_payment)

        VALIDACIONES:
        1. Debe tener received_in_wallet_id
        2. total_final_amount debe ser > 0
        3. NO debe existir transacción previa (idempotencia)

        Args:
            db: Database session
            payment: Payment a procesar
            old_status: Estado anterior del payment

        Returns:
            FinancialTransactions creada, o None si no se procesa

        Raises:
            ValueError: Si faltan validaciones o transacción ya existe
        """

        # Solo procesar cuando cambia a 'paid'
        if payment.payment_status != 'paid' or old_status == 'paid':
            return None

        # VALIDACIÓN 1: Debe tener wallet_id
        if not payment.received_in_wallet_id:
            error_msg = "Debe especificar received_in_wallet_id para marcar como pagado"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)

        # VALIDACIÓN 2: Solo si total_final_amount > 0
        if payment.total_final_amount <= 0:
            error_msg = (
                f"No se puede marcar como paid con saldo negativo o cero "
                f"(total_final_amount: {payment.total_final_amount})"
            )
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)

        # VALIDACIÓN 3: Verificar que NO exista transacción previa (idempotencia)
        existing_txn = db.query(FinancialTransactions).filter(
            FinancialTransactions.reference_type == 'payment',
            FinancialTransactions.reference_id == payment.payment_id
        ).first()

        if existing_txn:
            error_msg = (
                f"Ya existe transacción {existing_txn.transaction_id} "
                f"para este payment {payment.payment_id}"
            )
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)

        # Generar ID de transacción
        transaction_id = IDGenerator.generate_transaction_id(db)

        # Construir descripción detallada
        description_parts = [
            f"Pago COD semanal",
            f"Carrier: {payment.carrier_id}",
            f"Semana: {payment.week_start_date}",
            f"Entregas: {payment.total_deliveries} ({payment.total_deliveries_amount} Bs)",
            f"Devoluciones: {payment.total_returns} ({payment.total_returns_amount} Bs)"
        ]

        if payment.previous_balance != 0:
            description_parts.append(f"Saldo anterior: {payment.previous_balance} Bs")

        description_parts.append(f"Total: {payment.total_final_amount} Bs")

        description = " - ".join(description_parts)

        # Crear transacción de ingreso
        transaction = FinancialTransactions(
            transaction_id=transaction_id,
            transaction_type='income',
            to_account_id=payment.received_in_wallet_id,
            amount=payment.total_final_amount,  # USA total_final_amount (incluye saldo anterior)
            currency='BOB',
            reference_type='payment',
            reference_id=payment.payment_id,
            description=description,
            transaction_date=payment.paid_date or datetime.now()
        )

        db.add(transaction)
        db.flush()

        logger.info(
            f"💰 Transacción financiera creada: {transaction_id} - "
            f"{payment.total_final_amount} BOB desde payment {payment.payment_id}"
        )

        return transaction

    # ==================== CONSULTAS ====================

    @staticmethod
    def get_payment(
        db: Session,
        payment_id: str
    ) -> Optional[Payments]:
        """
        Obtener payment por ID

        Args:
            db: Database session
            payment_id: ID del payment

        Returns:
            Payment si existe, None si no
        """

        return db.query(Payments).filter(
            Payments.payment_id == payment_id
        ).first()

    @staticmethod
    def get_carrier_payments(
        db: Session,
        carrier_id: str,
        limit: int = 10
    ) -> list[Payments]:
        """
        Obtener payments de un carrier (más recientes primero)

        Args:
            db: Database session
            carrier_id: ID del carrier
            limit: Límite de resultados

        Returns:
            Lista de payments
        """

        return db.query(Payments).filter(
            Payments.carrier_id == carrier_id
        ).order_by(Payments.week_start_date.desc()).limit(limit).all()

    # ==================== PROCESAMIENTO POR LOTES ====================

    @staticmethod
    def batch_mark_payments_as_paid(
        db: Session,
        payment_ids: list[str],
        received_in_wallet_id: str,
        paid_date: Optional[datetime] = None
    ) -> dict:
        """
        Marcar múltiples payments como pagados en una sola operación (BATCH PROCESSING)

        VALIDACIONES:
        - Todos los payments deben existir
        - Todos deben estar en status 'pending'
        - Todos deben tener total_final_amount > 0
        - Todos deben del mismo carrier (opcional, para seguridad)

        Args:
            db: Database session
            payment_ids: Lista de payment_ids a marcar como pagados
            received_in_wallet_id: ID de la wallet donde se recibió el pago
            paid_date: Fecha de pago (default: ahora)

        Returns:
            Dict con resumen del procesamiento por lotes
        """
        try:
            if not payment_ids:
                raise ValueError("La lista de payment_ids está vacía")

            if not received_in_wallet_id:
                raise ValueError("Debe especificar received_in_wallet_id")

            # Usar fecha actual si no se especifica
            if not paid_date:
                paid_date = datetime.now()

            # PASO 1: Obtener todos los payments
            payments = db.query(Payments).filter(
                Payments.payment_id.in_(payment_ids)
            ).all()

            if len(payments) != len(payment_ids):
                found_ids = {p.payment_id for p in payments}
                missing_ids = set(payment_ids) - found_ids
                raise ValueError(f"No se encontraron estos payment_ids: {missing_ids}")

            # PASO 2: Validaciones previas
            invalid_payments = []
            carrier_ids = set()

            for payment in payments:
                carrier_ids.add(payment.carrier_id)

                # Validar status
                if payment.payment_status != 'pending':
                    invalid_payments.append({
                        'payment_id': payment.payment_id,
                        'reason': f'Status actual: {payment.payment_status} (debe ser pending)'
                    })

                # Validar monto
                if payment.total_final_amount <= 0:
                    invalid_payments.append({
                        'payment_id': payment.payment_id,
                        'reason': f'Total_final_amount: {payment.total_final_amount} (debe ser > 0)'
                    })

            if invalid_payments:
                error_msg = f"Payments inválidos encontrados: {invalid_payments}"
                logger.error(f"❌ {error_msg}")
                raise ValueError(error_msg)

            # PASO 3: Procesar cada payment
            total_amount_processed = Decimal('0')
            transactions_created = []

            for payment in payments:
                # Marcar como paid
                old_status = payment.payment_status
                payment.payment_status = 'paid'
                payment.received_in_wallet_id = received_in_wallet_id
                payment.paid_date = paid_date
                db.flush()

                # Crear transacción financiera
                transaction = PaymentService.create_transaction_from_payment(
                    db=db,
                    payment=payment,
                    old_status=old_status
                )

                if transaction:
                    total_amount_processed += payment.total_final_amount
                    transactions_created.append(transaction.transaction_id)

            db.commit()

            result = {
                'success': True,
                'payments_processed': len(payments),
                'total_amount': float(total_amount_processed),
                'currency': 'BOB',
                'received_in_wallet_id': received_in_wallet_id,
                'paid_date': paid_date.isoformat(),
                'transactions_created': transactions_created,
                'carriers_involved': list(carrier_ids)
            }

            logger.info(
                f"✅ BATCH PROCESSING COMPLETADO: {len(payments)} payments marcados como paid, "
                f"total procesado: {total_amount_processed} BOB"
            )

            return result

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error en batch processing: {str(e)}")
            raise ValueError(f"Error en batch processing: {str(e)}")

    # ==================== VALIDACIÓN DE BALANCE NEGATIVO EXCESIVO ====================

    @staticmethod
    def check_excessive_negative_balance_alerts(
        db: Session,
        threshold_amount: Decimal = Decimal('-10000'),
        threshold_weeks: int = 2
    ) -> list[dict]:
        """
        Detectar carriers con balance negativo excesivo durante período prolongado

        REGLA:
        Alertar si carrier tiene:
        - total_final_amount < threshold_amount (default: -10,000 BOB)
        - Durante más de threshold_weeks semanas consecutivas (default: 2 semanas)

        Args:
            db: Database session
            threshold_amount: Umbral de balance negativo (default: -10,000 BOB)
            threshold_weeks: Número de semanas consecutivas (default: 2)

        Returns:
            Lista de alertas con carriers en riesgo
        """
        from sqlalchemy import func, and_

        # Calcular fecha de hace N semanas
        weeks_ago = datetime.now() - timedelta(weeks=threshold_weeks)

        # Buscar carriers con múltiples semanas consecutivas en negativo
        carriers_at_risk = []

        # Obtener todos los carriers únicos con payments
        carriers = db.query(Payments.carrier_id).distinct().all()

        for (carrier_id,) in carriers:
            # Obtener últimos N+1 payments del carrier (ordenados por fecha)
            recent_payments = db.query(Payments).filter(
                Payments.carrier_id == carrier_id,
                Payments.week_start_date >= weeks_ago.date()
            ).order_by(
                Payments.week_start_date.desc()
            ).limit(threshold_weeks + 1).all()

            if len(recent_payments) < threshold_weeks:
                # No tiene suficientes semanas de datos
                continue

            # Verificar si TODAS las últimas N semanas están por debajo del umbral
            consecutive_negative_weeks = 0
            total_debt = Decimal('0')
            weeks_detail = []

            for payment in recent_payments[:threshold_weeks]:
                if payment.total_final_amount < threshold_amount:
                    consecutive_negative_weeks += 1
                    total_debt += payment.total_final_amount
                    weeks_detail.append({
                        'week_start': payment.week_start_date.isoformat(),
                        'balance': float(payment.total_final_amount)
                    })
                else:
                    break  # No son consecutivas

            # Si todas las últimas N semanas están negativas
            if consecutive_negative_weeks >= threshold_weeks:
                # Obtener info del carrier
                carrier = db.query(Carriers).filter(
                    Carriers.carrier_id == carrier_id
                ).first()

                carriers_at_risk.append({
                    'carrier_id': carrier_id,
                    'carrier_name': carrier.full_name if carrier else 'N/A',
                    'carrier_phone': carrier.phone if carrier else 'N/A',
                    'consecutive_negative_weeks': consecutive_negative_weeks,
                    'total_accumulated_debt': float(total_debt),
                    'average_weekly_debt': float(total_debt / consecutive_negative_weeks),
                    'threshold_amount': float(threshold_amount),
                    'weeks_detail': weeks_detail,
                    'alert_level': 'CRITICAL' if total_debt < (threshold_amount * 2) else 'HIGH',
                    'recommendation': 'Contactar carrier urgente para regularizar pagos'
                })

        if carriers_at_risk:
            logger.warning(
                f"⚠️ ALERTA: {len(carriers_at_risk)} carriers con balance negativo excesivo detectados"
            )
        else:
            logger.info(f"✅ No hay carriers con balance negativo excesivo")

        return carriers_at_risk

    @staticmethod
    def get_carrier_balance_trend(
        db: Session,
        carrier_id: str,
        weeks: int = 8
    ) -> dict:
        """
        Obtener tendencia de balance de un carrier en las últimas N semanas

        Args:
            db: Database session
            carrier_id: ID del carrier
            weeks: Número de semanas a analizar (default: 8)

        Returns:
            Dict con tendencia de balance y métricas
        """
        # Calcular fecha de hace N semanas
        weeks_ago = datetime.now() - timedelta(weeks=weeks)

        # Obtener payments del carrier en el período
        payments = db.query(Payments).filter(
            and_(
                Payments.carrier_id == carrier_id,
                Payments.week_start_date >= weeks_ago.date()
            )
        ).order_by(
            Payments.week_start_date.asc()
        ).all()

        if not payments:
            return {
                'carrier_id': carrier_id,
                'weeks_analyzed': 0,
                'trend': 'NO_DATA',
                'message': 'No hay datos de payments en el período especificado'
            }

        # Analizar tendencia
        balances = [float(p.total_final_amount) for p in payments]
        weeks_data = []

        for p in payments:
            weeks_data.append({
                'week_start': p.week_start_date.isoformat(),
                'balance': float(p.total_final_amount),
                'deliveries': p.total_deliveries,
                'returns': p.total_returns,
                'status': p.payment_status
            })

        # Calcular métricas
        avg_balance = sum(balances) / len(balances)
        min_balance = min(balances)
        max_balance = max(balances)

        # Determinar tendencia (simple: comparar primera mitad vs segunda mitad)
        mid_point = len(balances) // 2
        first_half_avg = sum(balances[:mid_point]) / mid_point if mid_point > 0 else 0
        second_half_avg = sum(balances[mid_point:]) / len(balances[mid_point:]) if len(balances[mid_point:]) > 0 else 0

        if second_half_avg > first_half_avg + 1000:
            trend = 'IMPROVING'
        elif second_half_avg < first_half_avg - 1000:
            trend = 'WORSENING'
        else:
            trend = 'STABLE'

        result = {
            'carrier_id': carrier_id,
            'weeks_analyzed': len(payments),
            'weeks_data': weeks_data,
            'avg_balance': round(avg_balance, 2),
            'min_balance': round(min_balance, 2),
            'max_balance': round(max_balance, 2),
            'current_balance': balances[-1] if balances else 0,
            'trend': trend,
            'is_at_risk': min_balance < -10000 or (trend == 'WORSENING' and avg_balance < -5000)
        }

        logger.info(
            f"📊 Tendencia de balance para carrier {carrier_id}: {trend}, "
            f"balance actual={result['current_balance']} BOB"
        )

        return result
