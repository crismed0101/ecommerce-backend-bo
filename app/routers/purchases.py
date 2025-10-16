"""
Router: PURCHASES

Endpoints para gestión de compras a proveedores

Características:
- Validación de precios de compra
- Historial de precios
- Alertas de cambios significativos
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from decimal import Decimal

from app.core.database import get_db
from app.core.exceptions import BaseAppException
from app.schemas.purchase import (
    PurchasePriceValidationRequest,
    PurchasePriceValidationResponse,
    PurchasePriceHistoryResponse,
    PurchasePriceHistoryEntry,
)
from app.services.purchase_service import PurchaseService

router = APIRouter(prefix="/api/v1/purchases", tags=["Purchases"])


@router.post(
    "/validate-price",
    response_model=PurchasePriceValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validar precio de compra antes de confirmar",
    description="""
    Validar si el precio de compra propuesto es razonable

    VALIDACIÓN CRÍTICA:
    - Compara nuevo precio con último precio de compra
    - Alerta si cambio supera umbral (default: 100%)
    - Previene errores en compras (ej: precio incorrecto del proveedor)

    **Niveles de alerta:**
    - CRITICAL: Cambio > 200%
    - HIGH: Cambio > threshold pero < 200%
    - NORMAL: Cambio < threshold

    **Ejemplo de uso:**
    Antes de confirmar una compra, validar que el precio unitario
    no haya cambiado drásticamente respecto a compras anteriores.

    Si el último precio era 100 BOB y el nuevo es 250 BOB (+150%),
    el sistema alertará para que verifiques con el proveedor.
    """,
)
def validate_purchase_price(
    validation: PurchasePriceValidationRequest,
    db: Session = Depends(get_db),
) -> PurchasePriceValidationResponse:
    """
    Validar precio de compra

    **Ejemplo:**
    ```json
    {
      "variant_id": "PRD00000001-1",
      "new_unit_price": 120.00,
      "threshold_percent": 100.0
    }
    ```

    **Respuesta con alerta:**
    ```json
    {
      "variant_id": "PRD00000001-1",
      "new_price": 250.00,
      "last_price": 100.00,
      "price_change": 150.00,
      "price_change_percent": 150.0,
      "threshold_percent": 100.0,
      "alert": true,
      "alert_level": "HIGH",
      "message": "ALERTA: Precio cambió +150% (de 100 a 250 BOB). Verificar con proveedor..."
    }
    ```
    """
    try:
        result = PurchaseService.validate_purchase_price_changes(
            db=db,
            product_variant_id=validation.variant_id,
            new_unit_price=Decimal(str(validation.new_unit_price)),
            threshold_percent=validation.threshold_percent
        )

        return PurchasePriceValidationResponse(
            variant_id=result['variant_id'],
            new_price=result['new_price'],
            last_price=result.get('last_price'),
            price_change=result.get('price_change'),
            price_change_percent=result.get('price_change_percent'),
            threshold_percent=result.get('threshold_percent', validation.threshold_percent),
            alert=result['alert'],
            alert_level=result.get('alert_level'),
            last_purchase_date=result.get('last_purchase_date'),
            message=result['message']
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)},
        )


@router.get(
    "/price-history/{variant_id}",
    response_model=PurchasePriceHistoryResponse,
    summary="Obtener historial de precios de compra",
    description="""
    Consultar historial completo de precios de compra de una variante

    INFORMACIÓN INCLUIDA:
    - Fecha de cada compra
    - Precio unitario pagado
    - Cantidad comprada
    - Proveedor
    - Moneda

    **Parámetro:**
    - limit: Número máximo de registros (default: 10)

    **Caso de uso:**
    - Análisis de tendencias de precios de proveedores
    - Negociación con proveedores
    - Detección de inflación en costos
    - Auditoría de compras
    """,
)
def get_purchase_price_history(
    variant_id: str,
    limit: int = Query(10, ge=1, le=100, description="Número máximo de registros"),
    db: Session = Depends(get_db),
) -> PurchasePriceHistoryResponse:
    """
    Obtener historial de precios de compra

    **Ejemplos de uso:**

    ```
    # Últimas 10 compras
    GET /api/v1/purchases/price-history/PRD00000001-1

    # Últimas 50 compras
    GET /api/v1/purchases/price-history/PRD00000001-1?limit=50
    ```
    """
    try:
        history = PurchaseService.get_purchase_price_history(
            db=db,
            product_variant_id=variant_id,
            limit=limit
        )

        history_entries = [
            PurchasePriceHistoryEntry(
                purchase_id=entry['purchase_id'],
                purchase_date=entry['purchase_date'],
                unit_cost=entry['unit_cost'],
                quantity=entry['quantity'],
                currency=entry['currency'],
                supplier_id=entry.get('supplier_id')
            )
            for entry in history
        ]

        return PurchasePriceHistoryResponse(
            success=True,
            variant_id=variant_id,
            total_records=len(history_entries),
            history=history_entries
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)},
        )
