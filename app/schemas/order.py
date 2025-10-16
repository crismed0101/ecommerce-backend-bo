"""
Schemas para Orders

Principio: Input validation + Output serialization
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ==================== ENUMS ====================

class DepartmentEnum(str, Enum):
    """Departamentos de Bolivia"""
    LA_PAZ = "LA_PAZ"
    COCHABAMBA = "COCHABAMBA"
    SANTA_CRUZ = "SANTA_CRUZ"
    ORURO = "ORURO"
    POTOSI = "POTOSI"
    TARIJA = "TARIJA"
    CHUQUISACA = "CHUQUISACA"
    BENI = "BENI"
    PANDO = "PANDO"


class PaymentMethodEnum(str, Enum):
    """Métodos de pago"""
    CASH_ON_DELIVERY = "CASH_ON_DELIVERY"
    BANK_TRANSFER = "BANK_TRANSFER"
    QR = "QR"


class OrderStatusEnum(str, Enum):
    """Estados de orden"""
    NEW = "new"
    CONFIRMED = "confirmed"
    DISPATCHED = "dispatched"
    DELIVERED = "delivered"
    RETURNED = "returned"
    CANCELLED = "cancelled"


# ==================== REQUEST SCHEMAS ====================

class CustomerCreate(BaseModel):
    """Crear/actualizar cliente"""
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: str = Field(..., min_length=7, max_length=15)
    email: Optional[EmailStr] = None
    department: str  # Ahora string (viene del adapter ya transformado)
    address: str = Field(..., min_length=5)
    reference: Optional[str] = None


class OrderItemCreate(BaseModel):
    """
    Item de orden (desde Shopify o manual)

    Soporta búsqueda por:
    - shopify_variant_id (si viene de Shopify)
    - sku (si cambió de tienda)
    - product_name (para crear si no existe)
    """
    shopify_product_id: Optional[int] = None
    shopify_variant_id: Optional[int] = None
    product_name: str
    sku: Optional[str] = None
    quantity: int = Field(..., gt=0, le=1000)
    unit_price: float = Field(..., gt=0)


class OrderCreate(BaseModel):
    """
    Crear orden completa

    Schema GENÉRICO que sirve para CUALQUIER fuente:
    - Shopify (via ShopifyAdapter)
    - WooCommerce (via WooCommerceAdapter)
    - N8N manual
    - Frontend web
    """
    # Customer
    customer: CustomerCreate

    # Items
    items: List[OrderItemCreate] = Field(..., min_length=1)

    # Shipping
    is_priority_shipping: bool = False
    priority_shipping_cost: float = 0.0
    carrier_id: Optional[str] = None

    # UTM tracking (para ROAS)
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None  # Ad external ID
    utm_term: Optional[str] = None

    # External reference (Shopify order ID, WooCommerce order ID, etc.)
    external_order_id: Optional[str] = None

    # Total y moneda
    total: float = Field(..., gt=0)
    currency: str = "BOB"

    # Notas
    notes: Optional[str] = None


class OrderStatusUpdate(BaseModel):
    """Actualizar estado de orden"""
    new_status: OrderStatusEnum
    notes: Optional[str] = None


# ==================== RESPONSE SCHEMAS ====================

class CustomerResponse(BaseModel):
    """Respuesta de customer"""
    customer_id: str
    full_name: str
    phone: str
    email: Optional[str]
    department: str
    total_orders: int
    total_spent_bob: float

    class Config:
        from_attributes = True  # Antes: orm_mode = True


class OrderItemResponse(BaseModel):
    """Respuesta de order item"""
    item_id: str
    product_variant_id: str
    product_name: str  # ← Ahora incluimos el nombre
    quantity: int
    unit_price: float
    subtotal: float

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    """Respuesta completa de orden"""
    order_id: str
    customer_id: str
    total: float
    is_priority_shipping: bool
    priority_shipping_cost: float
    current_status: str
    items: List[OrderItemResponse]
    utm_source: Optional[str]
    utm_content: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class OrderCreateResponse(BaseModel):
    """Respuesta al crear orden"""
    success: bool
    order_id: str
    customer_id: str
    total_items: int
    total_amount: float
    message: str

    # Info adicional útil
    products_created: int = 0  # Cuántos productos se crearon automáticamente
    warnings: List[str] = []  # Advertencias (ej: "Producto X creado automáticamente")


class OrderListItem(BaseModel):
    """Item individual en lista de órdenes (resumen)"""
    order_id: str
    customer_id: str
    customer_name: str
    total: float
    current_status: str
    carrier_id: Optional[str]
    external_order_id: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    """Respuesta de lista de órdenes con paginación"""
    success: bool = True
    total: int  # Total de órdenes que cumplen los filtros
    page: int
    page_size: int
    total_pages: int
    orders: List[OrderListItem]
