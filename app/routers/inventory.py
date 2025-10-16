"""
Router: INVENTORY

Endpoints para gestión de inventario

Características:
- Transferencias entre departamentos
- Alertas de stock bajo
- Ajustes con auditoría
- Rotación de inventario
- Valuación FIFO/LIFO
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.exceptions import BaseAppException
from app.schemas.inventory import (
    StockTransferRequest,
    StockTransferResponse,
    LowStockAlertsResponse,
    LowStockAlert,
    InventoryAdjustmentRequest,
    InventoryAdjustmentResponse,
    InventoryTurnoverResponse,
    InventoryValuationResponse,
    ValuationMethodEnum,
)
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/api/v1/inventory", tags=["Inventory"])


@router.post(
    "/transfer",
    response_model=StockTransferResponse,
    status_code=status.HTTP_200_OK,
    summary="Transferir stock entre departamentos",
    description="""
    Transferir stock de un departamento a otro de manera atómica

    FLUJO:
    1. Validar stock disponible en departamento origen
    2. Crear movimiento de salida (transfer_out)
    3. Crear movimiento de entrada (transfer_in)
    4. Actualizar stock en ambos departamentos

    Todo en una sola transacción ACID.
    """,
)
def transfer_stock(
    transfer: StockTransferRequest,
    db: Session = Depends(get_db),
) -> StockTransferResponse:
    """
    Transferir stock entre departamentos

    **Ejemplo:**
    ```json
    {
      "variant_id": "PRD00000001-1",
      "from_department": "LA_PAZ",
      "to_department": "COCHABAMBA",
      "quantity": 10,
      "notes": "Transferencia por mayor demanda en Cochabamba"
    }
    ```
    """
    try:
        result = InventoryService.transfer_stock_between_departments(
            db=db,
            variant_id=transfer.variant_id,
            from_department=transfer.from_department.value,
            to_department=transfer.to_department.value,
            quantity=transfer.quantity,
            notes=transfer.notes
        )

        return StockTransferResponse(
            success=True,
            variant_id=result['variant_id'],
            from_department=result['from_department'],
            to_department=result['to_department'],
            quantity=result['quantity'],
            transfer_out_movement_id=result['transfer_out_movement_id'],
            transfer_in_movement_id=result['transfer_in_movement_id'],
            new_stock_from=result['new_stock_from'],
            new_stock_to=result['new_stock_to'],
            message=result['message']
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_error", "message": str(e)},
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)},
        )


@router.get(
    "/alerts/low-stock",
    response_model=LowStockAlertsResponse,
    summary="Obtener alertas de stock bajo",
    description="""
    Listar variantes con stock bajo por departamento

    ALERTAS:
    - CRITICAL: stock = 0 (sin inventario)
    - WARNING: stock < umbral mínimo configurado

    **Filtros:**
    - department: Filtrar por departamento específico (opcional)
    - min_threshold: Umbral mínimo personalizado (default: 5)
    """,
)
def get_low_stock_alerts(
    department: Optional[str] = Query(None, description="Departamento a verificar (opcional)"),
    min_threshold: int = Query(5, ge=0, description="Umbral mínimo de stock"),
    db: Session = Depends(get_db),
) -> LowStockAlertsResponse:
    """
    Obtener alertas de stock bajo

    **Ejemplos de uso:**

    ```
    # Todas las alertas (todos los departamentos)
    GET /api/v1/inventory/alerts/low-stock

    # Alertas solo para La Paz
    GET /api/v1/inventory/alerts/low-stock?department=LA_PAZ

    # Alertas con umbral personalizado (stock < 10)
    GET /api/v1/inventory/alerts/low-stock?min_threshold=10
    ```
    """
    try:
        alerts = InventoryService.check_low_stock_alerts(
            db=db,
            department=department,
            min_threshold=min_threshold
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

            alert_items.append(LowStockAlert(
                variant_id=alert['variant_id'],
                product_name=alert.get('product_name'),
                sku=alert.get('sku'),
                department=alert['department'],
                current_stock=alert['current_stock'],
                min_stock_threshold=alert['min_stock_threshold'],
                shortage=alert['shortage'],
                alert_level=alert_level
            ))

        return LowStockAlertsResponse(
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


@router.post(
    "/adjustment",
    response_model=InventoryAdjustmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Crear ajuste de inventario con auditoría",
    description="""
    Ajustar inventario por pérdidas, daños, o correcciones

    CARACTERÍSTICAS:
    - Auditoría completa: reason obligatorio
    - Ajustes positivos o negativos
    - Genera movimiento de tipo 'adjustment'
    - Actualiza stock inmediatamente

    **Razones comunes:**
    - "Daño en almacén"
    - "Pérdida por robo"
    - "Corrección de conteo físico"
    - "Producto vencido"
    """,
)
def create_adjustment(
    adjustment: InventoryAdjustmentRequest,
    db: Session = Depends(get_db),
) -> InventoryAdjustmentResponse:
    """
    Crear ajuste de inventario

    **Ejemplo (ajuste negativo - pérdida):**
    ```json
    {
      "variant_id": "PRD00000001-1",
      "department": "LA_PAZ",
      "quantity": -5,
      "reason": "Daño en almacén durante inventario físico",
      "notes": "Productos con empaque dañado, no aptos para venta"
    }
    ```

    **Ejemplo (ajuste positivo - corrección):**
    ```json
    {
      "variant_id": "PRD00000002-1",
      "department": "COCHABAMBA",
      "quantity": 3,
      "reason": "Corrección de conteo físico - se encontraron 3 unidades adicionales",
      "notes": "Error en conteo anterior"
    }
    ```
    """
    try:
        result = InventoryService.create_adjustment_with_audit(
            db=db,
            variant_id=adjustment.variant_id,
            department=adjustment.department.value,
            quantity=adjustment.quantity,
            reason=adjustment.reason,
            notes=adjustment.notes
        )

        return InventoryAdjustmentResponse(
            success=True,
            variant_id=result['variant_id'],
            department=result['department'],
            adjustment_quantity=result['adjustment_quantity'],
            previous_stock=result['previous_stock'],
            new_stock=result['new_stock'],
            movement_id=result['movement_id'],
            reason=result['reason'],
            message=result['message']
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_error", "message": str(e)},
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)},
        )


@router.get(
    "/turnover/{variant_id}",
    response_model=InventoryTurnoverResponse,
    summary="Calcular rotación de inventario",
    description="""
    Calcular rotación de inventario (Inventory Turnover) de una variante

    MÉTRICAS:
    - Turnover Rate: ventas / stock promedio
    - Days of Supply: días de inventario disponible

    **Interpretación:**
    - Alta rotación (>10): Producto muy vendido
    - Media rotación (5-10): Producto estable
    - Baja rotación (<5): Producto lento
    """,
)
def get_inventory_turnover(
    variant_id: str,
    days: int = Query(30, ge=1, le=365, description="Período en días (default: 30)"),
    db: Session = Depends(get_db),
) -> InventoryTurnoverResponse:
    """
    Calcular rotación de inventario

    **Ejemplos de uso:**

    ```
    # Rotación últimos 30 días
    GET /api/v1/inventory/turnover/PRD00000001-1

    # Rotación últimos 90 días
    GET /api/v1/inventory/turnover/PRD00000001-1?days=90
    ```
    """
    try:
        result = InventoryService.calculate_inventory_turnover(
            db=db,
            variant_id=variant_id,
            days=days
        )

        return InventoryTurnoverResponse(
            success=True,
            variant_id=result['variant_id'],
            product_name=result.get('product_name'),
            days=result['days'],
            total_sales=result['total_sales'],
            avg_stock=result['avg_stock'],
            turnover_rate=result['turnover_rate'],
            days_of_supply=result.get('days_of_supply'),
            interpretation=result['interpretation'],
            message=result['message']
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)},
        )


@router.get(
    "/valuation/{variant_id}",
    response_model=InventoryValuationResponse,
    summary="Calcular valuación de inventario (FIFO/LIFO)",
    description="""
    Calcular valor del inventario usando FIFO o LIFO

    MÉTODOS:
    - FIFO (First In, First Out): Primeras compras salen primero
    - LIFO (Last In, First Out): Últimas compras salen primero

    **Uso:**
    - FIFO: Más común, refleja costo actual
    - LIFO: Útil para inflación
    """,
)
def get_inventory_valuation(
    variant_id: str,
    department: str = Query(..., description="Departamento a valuar"),
    method: ValuationMethodEnum = Query(ValuationMethodEnum.FIFO, description="Método de valuación"),
    db: Session = Depends(get_db),
) -> InventoryValuationResponse:
    """
    Calcular valuación de inventario

    **Ejemplos de uso:**

    ```
    # Valuación FIFO para La Paz
    GET /api/v1/inventory/valuation/PRD00000001-1?department=LA_PAZ&method=fifo

    # Valuación LIFO para Cochabamba
    GET /api/v1/inventory/valuation/PRD00000001-1?department=COCHABAMBA&method=lifo
    ```
    """
    try:
        if method == ValuationMethodEnum.FIFO:
            result = InventoryService.calculate_inventory_value_fifo(
                db=db,
                variant_id=variant_id,
                department=department
            )
        else:  # LIFO
            result = InventoryService.calculate_inventory_value_lifo(
                db=db,
                variant_id=variant_id,
                department=department
            )

        return InventoryValuationResponse(
            success=True,
            variant_id=result['variant_id'],
            product_name=result.get('product_name'),
            department=result['department'],
            current_stock=result['current_stock'],
            valuation_method=result['method'],
            unit_cost=result['unit_cost'],
            total_value=result['total_value'],
            currency=result['currency'],
            message=result['message']
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)},
        )
