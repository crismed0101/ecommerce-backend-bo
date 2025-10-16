"""
Router: PAYMENTS

Endpoints para gestión de pagos a carriers

Características:
- Procesamiento en lote de pagos
- Alertas de balances negativos críticos
- Análisis de tendencias de balance
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.exceptions import BaseAppException
from app.schemas.payment import (
    BatchPaymentRequest,
    BatchPaymentResponse,
    PaymentProcessed,
    NegativeBalanceAlertsResponse,
    NegativeBalanceAlert,
    CarrierBalanceTrendResponse,
    BalanceTrendPoint,
)
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])


@router.post(
    "/batch-paid",
    response_model=BatchPaymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Marcar múltiples pagos como pagados en lote",
    description="""
    Procesar múltiples pagos a carriers en una sola operación

    CARACTERÍSTICAS:
    - Procesamiento atómico (todo o nada)
    - Actualiza balances de carriers
    - Genera transacciones financieras
    - Auditoría completa

    **Caso de uso:**
    Al final del mes, marcar como pagados todos los pagos pendientes de un carrier

    **Validaciones:**
    - Solo procesa pagos en estado 'pending'
    - Valida que exista account del carrier
    - Registra fecha de pago
    """,
)
def batch_mark_as_paid(
    batch: BatchPaymentRequest,
    db: Session = Depends(get_db),
) -> BatchPaymentResponse:
    """
    Marcar pagos en lote como pagados

    **Ejemplo:**
    ```json
    {
      "payment_ids": [
        "PAY00000001",
        "PAY00000002",
        "PAY00000003"
      ],
      "payment_date": "2025-10-15T10:30:00",
      "notes": "Pago mensual a carrier - Octubre 2025"
    }
    ```
    """
    try:
        results = PaymentService.batch_mark_payments_as_paid(
            db=db,
            payment_ids=batch.payment_ids,
            payment_date=batch.payment_date,
            notes=batch.notes
        )

        payments = []
        total_processed = 0
        total_failed = 0
        total_amount = 0.0

        for result in results:
            if result['status'] == 'success':
                total_processed += 1
                total_amount += result['amount']
            else:
                total_failed += 1

            payments.append(PaymentProcessed(
                payment_id=result['payment_id'],
                order_id=result.get('order_id', 'N/A'),
                carrier_id=result.get('carrier_id', 'N/A'),
                amount=result['amount'],
                currency=result.get('currency', 'BOB'),
                status=result['status'],
                message=result['message']
            ))

        return BatchPaymentResponse(
            success=total_failed == 0,
            total_requested=len(batch.payment_ids),
            total_processed=total_processed,
            total_failed=total_failed,
            total_amount_processed=total_amount,
            currency='BOB',
            payments=payments,
            message=f"Procesados {total_processed}/{len(batch.payment_ids)} pagos exitosamente"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)},
        )


@router.get(
    "/alerts/negative-balance",
    response_model=NegativeBalanceAlertsResponse,
    summary="Obtener alertas de carriers con balance negativo excesivo",
    description="""
    Detectar carriers con balances negativos críticos

    ALERTAS CRÍTICAS:
    - Balance < -10,000 BOB por más de 14 días (default)
    - Indica posible problema de liquidez del carrier

    **Parámetros personalizables:**
    - threshold_amount: Monto mínimo de balance negativo (default: -10000)
    - threshold_days: Días en negativo para alertar (default: 14)

    **Caso de uso:**
    Dashboard financiero para identificar carriers con riesgo de incumplimiento
    """,
)
def get_negative_balance_alerts(
    threshold_amount: float = Query(-10000.0, le=0, description="Umbral de balance negativo (ej: -10000)"),
    threshold_days: int = Query(14, ge=1, description="Días en negativo para alertar"),
    db: Session = Depends(get_db),
) -> NegativeBalanceAlertsResponse:
    """
    Obtener alertas de balance negativo

    **Ejemplos de uso:**

    ```
    # Alertas con umbrales por defecto (< -10,000 BOB por 14+ días)
    GET /api/v1/payments/alerts/negative-balance

    # Alertas más estrictas (< -5,000 BOB por 7+ días)
    GET /api/v1/payments/alerts/negative-balance?threshold_amount=-5000&threshold_days=7
    ```
    """
    try:
        alerts = PaymentService.check_excessive_negative_balance_alerts(
            db=db,
            threshold_amount=threshold_amount,
            threshold_days=threshold_days
        )

        alert_items = []
        critical_count = 0
        warning_count = 0

        for alert in alerts:
            alert_level = alert['alert_level']
            if alert_level == 'CRITICAL':
                critical_count += 1
            else:
                warning_count += 1

            alert_items.append(NegativeBalanceAlert(
                carrier_id=alert['carrier_id'],
                carrier_name=alert.get('carrier_name'),
                current_balance=alert['current_balance'],
                days_negative=alert['days_negative'],
                threshold_days=alert['threshold_days'],
                threshold_amount=alert['threshold_amount'],
                alert_level=alert_level,
                message=alert['message']
            ))

        return NegativeBalanceAlertsResponse(
            success=True,
            total_alerts=len(alerts),
            critical_alerts=critical_count,
            warning_alerts=warning_count,
            alerts=alert_items
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)},
        )


@router.get(
    "/balance-trend/{carrier_id}",
    response_model=CarrierBalanceTrendResponse,
    summary="Obtener tendencia de balance de un carrier",
    description="""
    Analizar evolución del balance de un carrier en el tiempo

    MÉTRICAS:
    - Tendencia: IMPROVING, STABLE, DECLINING
    - Cambio promedio diario
    - Serie temporal de balances

    **Uso:**
    - Identificar si un carrier está mejorando o empeorando su balance
    - Predecir problemas futuros de liquidez
    - Decisiones de crédito

    **Parámetro:**
    - days: Período a analizar (default: 30 días)
    """,
)
def get_carrier_balance_trend(
    carrier_id: str,
    days: int = Query(30, ge=7, le=365, description="Período en días (default: 30)"),
    db: Session = Depends(get_db),
) -> CarrierBalanceTrendResponse:
    """
    Obtener tendencia de balance de carrier

    **Ejemplos de uso:**

    ```
    # Tendencia últimos 30 días
    GET /api/v1/payments/balance-trend/CAR00000001

    # Tendencia últimos 90 días
    GET /api/v1/payments/balance-trend/CAR00000001?days=90
    ```
    """
    try:
        result = PaymentService.get_carrier_balance_trend(
            db=db,
            carrier_id=carrier_id,
            days=days
        )

        trend_points = [
            BalanceTrendPoint(
                date=point['date'],
                balance=point['balance']
            )
            for point in result['trend_data']
        ]

        return CarrierBalanceTrendResponse(
            success=True,
            carrier_id=result['carrier_id'],
            carrier_name=result.get('carrier_name'),
            current_balance=result['current_balance'],
            currency=result['currency'],
            days=result['days'],
            trend_direction=result['trend_direction'],
            avg_daily_change=result['avg_daily_change'],
            trend_data=trend_points,
            message=result['message']
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": str(e)},
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)},
        )
