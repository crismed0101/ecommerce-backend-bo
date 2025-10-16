"""
Schemas para Products

Principio: Input validation + Output serialization
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ==================== ENUMS ====================

class RecommendationTypeEnum(str, Enum):
    """Tipos de recomendación de productos"""
    UPSELL = "upsell"
    CROSS_SELL = "cross_sell"


# ==================== REQUEST SCHEMAS ====================

class VariantPriceUpdateRequest(BaseModel):
    """Actualizar precio de variante con historial"""
    new_price: float = Field(..., gt=0, description="Nuevo precio de venta")
    reason: Optional[str] = Field(None, max_length=500, description="Razón del cambio de precio")


class AddRelatedProductRequest(BaseModel):
    """Agregar producto relacionado"""
    related_product_id: str = Field(..., description="ID del producto relacionado")
    recommendation_type: RecommendationTypeEnum = Field(..., description="Tipo de recomendación")
    priority: Optional[int] = Field(1, ge=1, le=10, description="Prioridad (1=más alta, 10=más baja)")


# ==================== RESPONSE SCHEMAS ====================

class PriceHistoryEntry(BaseModel):
    """Entrada de historial de precios"""
    price: float
    effective_date: datetime
    reason: Optional[str]


class VariantPriceUpdateResponse(BaseModel):
    """Respuesta de actualización de precio"""
    success: bool
    variant_id: str
    product_name: Optional[str]
    sku: Optional[str]
    old_price: float
    new_price: float
    price_change: float
    price_change_percent: float
    effective_date: datetime
    message: str


class PriceChangeAlert(BaseModel):
    """Alerta de cambio de precio"""
    variant_id: str
    product_name: Optional[str]
    sku: Optional[str]
    old_price: float
    new_price: float
    price_change: float
    price_change_percent: float
    change_date: datetime
    alert_level: str  # "MAJOR_INCREASE", "MAJOR_DECREASE", "NORMAL"


class PriceChangeAlertsResponse(BaseModel):
    """Respuesta de alertas de cambios de precio"""
    success: bool
    days: int
    total_changes: int
    major_increases: int
    major_decreases: int
    alerts: List[PriceChangeAlert]


class RelatedProduct(BaseModel):
    """Producto relacionado"""
    product_id: str
    product_name: str
    category: Optional[str]
    recommendation_type: str
    priority: int


class RelatedProductsResponse(BaseModel):
    """Respuesta de productos relacionados"""
    success: bool
    product_id: str
    product_name: Optional[str]
    total_related: int
    related_products: List[RelatedProduct]


class AddRelatedProductResponse(BaseModel):
    """Respuesta al agregar producto relacionado"""
    success: bool
    product_id: str
    related_product_id: str
    recommendation_type: str
    message: str


class RecommendedProduct(BaseModel):
    """Producto recomendado para upsell/cross-sell"""
    product_id: str
    product_name: str
    category: Optional[str]
    avg_price: float
    recommendation_score: float
    recommendation_reason: str


class ProductRecommendationsResponse(BaseModel):
    """Respuesta de recomendaciones de productos"""
    success: bool
    product_id: str
    product_name: Optional[str]
    recommendation_type: str  # "upsell" or "cross_sell"
    total_recommendations: int
    recommendations: List[RecommendedProduct]
