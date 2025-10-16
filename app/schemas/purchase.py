"""
Schemas para Purchases

Principio: Input validation + Output serialization
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# ==================== REQUEST SCHEMAS ====================

class PurchasePriceValidationRequest(BaseModel):
    """Validar precio de compra antes de confirmar"""
    variant_id: str = Field(..., description="ID de la variante de producto")
    new_unit_price: float = Field(..., gt=0, description="Nuevo precio unitario propuesto")
    threshold_percent: Optional[float] = Field(
        100.0,
        ge=0,
        description="Umbral de cambio porcentual para alertar (default: 100%)"
    )


# ==================== RESPONSE SCHEMAS ====================

class PurchasePriceValidationResponse(BaseModel):
    """Respuesta de validación de precio de compra"""
    variant_id: str
    new_price: float
    last_price: Optional[float]
    price_change: Optional[float]
    price_change_percent: Optional[float]
    threshold_percent: float
    alert: bool
    alert_level: Optional[str]  # "CRITICAL", "HIGH", "NORMAL"
    last_purchase_date: Optional[str]
    message: str


class PurchasePriceHistoryEntry(BaseModel):
    """Entrada de historial de precios de compra"""
    purchase_id: str
    purchase_date: str  # ISO format
    unit_cost: float
    quantity: float
    currency: str
    supplier_id: Optional[str]


class PurchasePriceHistoryResponse(BaseModel):
    """Respuesta de historial de precios de compra"""
    success: bool
    variant_id: str
    total_records: int
    history: List[PurchasePriceHistoryEntry]
