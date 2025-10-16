"""
Schemas para Payments

Principio: Input validation + Output serialization
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ==================== REQUEST SCHEMAS ====================

class BatchPaymentRequest(BaseModel):
    """Marcar múltiples pagos como pagados en lote"""
    payment_ids: List[str] = Field(..., min_length=1, description="Lista de payment IDs a marcar como pagados")
    payment_date: Optional[datetime] = Field(None, description="Fecha de pago (default: hoy)")
    notes: Optional[str] = Field(None, max_length=500, description="Notas sobre el pago en lote")


# ==================== RESPONSE SCHEMAS ====================

class PaymentProcessed(BaseModel):
    """Pago individual procesado en lote"""
    payment_id: str
    order_id: str
    carrier_id: str
    amount: float
    currency: str
    status: str  # "success" or "error"
    message: str


class BatchPaymentResponse(BaseModel):
    """Respuesta de procesamiento de pagos en lote"""
    success: bool
    total_requested: int
    total_processed: int
    total_failed: int
    total_amount_processed: float
    currency: str
    payments: List[PaymentProcessed]
    message: str


class NegativeBalanceAlert(BaseModel):
    """Alerta de balance negativo excesivo"""
    carrier_id: str
    carrier_name: Optional[str]
    current_balance: float
    days_negative: int
    threshold_days: int
    threshold_amount: float
    alert_level: str  # "CRITICAL", "WARNING"
    message: str


class NegativeBalanceAlertsResponse(BaseModel):
    """Respuesta de alertas de balance negativo"""
    success: bool
    total_alerts: int
    critical_alerts: int
    warning_alerts: int
    alerts: List[NegativeBalanceAlert]


class BalanceTrendPoint(BaseModel):
    """Punto de tendencia de balance"""
    date: str  # YYYY-MM-DD
    balance: float


class CarrierBalanceTrendResponse(BaseModel):
    """Respuesta de tendencia de balance de carrier"""
    success: bool
    carrier_id: str
    carrier_name: Optional[str]
    current_balance: float
    currency: str
    days: int
    trend_direction: str  # "IMPROVING", "STABLE", "DECLINING"
    avg_daily_change: float
    trend_data: List[BalanceTrendPoint]
    message: str
