"""
Schemas para Inventory

Principio: Input validation + Output serialization
"""

from pydantic import BaseModel, Field
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


class MovementTypeEnum(str, Enum):
    """Tipos de movimiento de inventario"""
    SALE = "sale"
    PURCHASE = "purchase"
    RETURN = "return"
    ADJUSTMENT = "adjustment"
    TRANSFER_OUT = "transfer_out"
    TRANSFER_IN = "transfer_in"


class ValuationMethodEnum(str, Enum):
    """Métodos de valuación de inventario"""
    FIFO = "fifo"
    LIFO = "lifo"


# ==================== REQUEST SCHEMAS ====================

class StockTransferRequest(BaseModel):
    """Transferir stock entre departamentos"""
    variant_id: str = Field(..., description="ID de la variante de producto")
    from_department: DepartmentEnum = Field(..., description="Departamento origen")
    to_department: DepartmentEnum = Field(..., description="Departamento destino")
    quantity: int = Field(..., gt=0, description="Cantidad a transferir")
    notes: Optional[str] = Field(None, max_length=500, description="Notas sobre la transferencia")


class InventoryAdjustmentRequest(BaseModel):
    """Crear ajuste de inventario con auditoría"""
    variant_id: str = Field(..., description="ID de la variante de producto")
    department: DepartmentEnum = Field(..., description="Departamento")
    quantity: int = Field(..., description="Cantidad del ajuste (positivo o negativo)")
    reason: str = Field(..., min_length=5, max_length=500, description="Razón del ajuste (obligatorio)")
    notes: Optional[str] = Field(None, max_length=1000, description="Notas adicionales")


# ==================== RESPONSE SCHEMAS ====================

class StockTransferResponse(BaseModel):
    """Respuesta de transferencia de stock"""
    success: bool
    variant_id: str
    from_department: str
    to_department: str
    quantity: int
    transfer_out_movement_id: str
    transfer_in_movement_id: str
    new_stock_from: int
    new_stock_to: int
    message: str


class LowStockAlert(BaseModel):
    """Alerta de stock bajo"""
    variant_id: str
    product_name: Optional[str]
    sku: Optional[str]
    department: str
    current_stock: int
    min_stock_threshold: int
    shortage: int
    alert_level: str  # "CRITICAL", "WARNING"


class LowStockAlertsResponse(BaseModel):
    """Respuesta de alertas de stock bajo"""
    success: bool
    total_alerts: int
    critical_alerts: int
    warning_alerts: int
    alerts: List[LowStockAlert]


class InventoryAdjustmentResponse(BaseModel):
    """Respuesta de ajuste de inventario"""
    success: bool
    variant_id: str
    department: str
    adjustment_quantity: int
    previous_stock: int
    new_stock: int
    movement_id: str
    reason: str
    message: str


class InventoryTurnoverResponse(BaseModel):
    """Respuesta de rotación de inventario"""
    success: bool
    variant_id: str
    product_name: Optional[str]
    days: int
    total_sales: int
    avg_stock: float
    turnover_rate: float
    days_of_supply: Optional[float]
    interpretation: str
    message: str


class InventoryValuationResponse(BaseModel):
    """Respuesta de valuación de inventario"""
    success: bool
    variant_id: str
    product_name: Optional[str]
    department: str
    current_stock: int
    valuation_method: str  # "FIFO" or "LIFO"
    unit_cost: float
    total_value: float
    currency: str
    message: str
