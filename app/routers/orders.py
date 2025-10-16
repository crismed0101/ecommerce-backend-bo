"""
Router: ORDERS

Endpoints minimalistas para gestión de órdenes

Principio YAGNI: Solo lo que necesitas AHORA
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
# from app.core.security import verify_token  # Comentado temporalmente
from app.core.exceptions import (
    InsufficientStockException,
    OrderNotFoundException,
    BaseAppException,
)
from app.schemas.order import (
    OrderCreate,
    OrderCreateResponse,
    OrderStatusUpdate,
    OrderResponse,
    OrderListResponse,
    OrderListItem,
)
from app.services.order_service import OrderService

router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])


@router.post(
    "",
    response_model=OrderCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear orden completa",
    description="""
    WRAPPER PRINCIPAL: Crea orden completa desde Shopify/N8N

    Hace:
    1. Crear/actualizar customer
    2. Validar stock
    3. Crear orden + items + tracking
    4. Actualizar customer stats

    Todo en una sola transacción (ACID).
    """,
)
def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    # token: dict = Depends(verify_token),  # Descomenta para requerir autenticación
) -> OrderCreateResponse:
    """
    Crear orden completa

    **Ejemplo:**
    ```json
    {
      "customer": {
        "full_name": "Juan Pérez",
        "phone": "70123456",
        "department": "LA_PAZ",
        "address": "Zona Sur #456"
      },
      "delivery_department": "LA_PAZ",
      "payment_method": "CASH_ON_DELIVERY",
      "utm_content": "23851234567890",
      "items": [
        {
          "product_variant_id": "PRD00000001-1",
          "quantity": 2,
          "unit_price": 150.00
        }
      ]
    }
    ```
    """
    try:
        return OrderService.create_full_order(db, order_data)

    except InsufficientStockException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "insufficient_stock",
                "message": e.message,
                "details": e.details,
            },
        )

    except BaseAppException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_error", "message": e.message},
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)},
        )


@router.patch(
    "/{order_id}/status",
    summary="Actualizar estado de orden",
    description="""
    Cambiar estado de orden

    Si status = 'delivered' → Reduce inventario automáticamente
    Si status = 'returned' → Aumenta inventario
    """,
)
def update_order_status(
    order_id: str,
    status_update: OrderStatusUpdate,
    db: Session = Depends(get_db),
    # token: dict = Depends(verify_token),
) -> dict:
    """
    Actualizar estado

    **Ejemplo:**
    ```json
    {
      "new_status": "delivered"
    }
    ```

    **Estados válidos:**
    - new
    - confirmed
    - dispatched
    - delivered (reduce stock)
    - returned (aumenta stock)
    - cancelled
    """
    try:
        tracking = OrderService.update_status(
            db=db,
            order_id=order_id,
            new_status=status_update.new_status,
            notes=status_update.notes
        )

        return {
            "success": True,
            "order_id": order_id,
            "new_status": tracking.order_status,
            "message": f"Estado actualizado a '{tracking.order_status}'"
        }

    except OrderNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "order_not_found", "message": e.message},
        )

    except BaseAppException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_error", "message": e.message},
        )


@router.get(
    "",
    response_model=OrderListResponse,
    summary="Listar órdenes con filtros y paginación",
    description="""
    Obtener lista de órdenes con filtros opcionales y paginación

    **Filtros disponibles:**
    - status: Filtrar por estado (new, confirmed, dispatched, delivered, returned, cancelled)
    - customer_id: Filtrar por ID de cliente
    - carrier_id: Filtrar por ID de transportista
    - external_order_id: Buscar por ID externo (coincidencia parcial)
    - date_from: Fecha desde (formato: YYYY-MM-DD)
    - date_to: Fecha hasta (formato: YYYY-MM-DD)

    **Paginación:**
    - page: Número de página (default: 1)
    - page_size: Cantidad por página (default: 20, max: 100)

    **Ordenamiento:**
    - Siempre ordenado por created_at DESC (más recientes primero)
    """,
)
def list_orders(
    status: Optional[str] = None,
    customer_id: Optional[str] = None,
    carrier_id: Optional[str] = None,
    external_order_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
) -> OrderListResponse:
    """
    Listar órdenes con filtros

    **Ejemplos de uso:**

    ```
    # Todas las órdenes (paginado)
    GET /api/v1/orders

    # Órdenes pendientes
    GET /api/v1/orders?status=new

    # Órdenes de un cliente específico
    GET /api/v1/orders?customer_id=CUS00000007

    # Órdenes de un carrier específico
    GET /api/v1/orders?carrier_id=CAR00000001

    # Órdenes entregadas entre dos fechas
    GET /api/v1/orders?status=delivered&date_from=2025-01-01&date_to=2025-01-31

    # Buscar por ID externo (Shopify, WooCommerce, etc.)
    GET /api/v1/orders?external_order_id=SHOPIFY-123

    # Combinación de filtros con paginación
    GET /api/v1/orders?status=delivered&carrier_id=CAR00000001&page=2&page_size=50
    ```
    """
    try:
        # Validar page_size
        if page_size > 100:
            page_size = 100
        if page_size < 1:
            page_size = 20

        # Validar page
        if page < 1:
            page = 1

        # Obtener órdenes con filtros
        orders, total = OrderService.get_orders_with_filters(
            db=db,
            status=status,
            customer_id=customer_id,
            carrier_id=carrier_id,
            external_order_id=external_order_id,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size
        )

        # Calcular total de páginas
        import math
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        # Construir lista de órdenes
        order_items = []
        for order in orders:
            order_items.append(OrderListItem(
                order_id=order.order_id,
                customer_id=order.customer_id,
                customer_name=order.customer.full_name if order.customer else "N/A",
                total=float(order.total),
                current_status=order.tracking.order_status if order.tracking else "unknown",
                carrier_id=order.carrier_id,
                external_order_id=order.external_order_id,
                created_at=order.created_at,
                updated_at=order.updated_at
            ))

        return OrderListResponse(
            success=True,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            orders=order_items
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)},
        )


@router.get(
    "/{order_id}",
    response_model=dict,
    summary="Obtener orden por ID",
    description="Retorna detalles completos de una orden con customer, items, y tracking",
)
def get_order(
    order_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """
    Obtener orden completa por ID

    Retorna:
    - Datos de la orden
    - Información del customer
    - Items de la orden con detalles de productos
    - Estado actual (tracking)

    **Ejemplo de respuesta:**
    ```json
    {
      "order_id": "ORD00000037",
      "customer": {
        "customer_id": "CUS00000007",
        "full_name": "Juan Pérez",
        "phone": "70123456",
        "department": "LA PAZ"
      },
      "total": 300.00,
      "current_status": "new",
      "items": [
        {
          "order_item_id": "ORD00000037-1",
          "product_name": "Chompa Roja",
          "quantity": 2,
          "unit_price": 150.00,
          "subtotal": 300.00
        }
      ],
      "created_at": "2025-10-15T10:30:00"
    }
    ```
    """
    try:
        # Buscar orden con joins
        order = OrderService.get_order(db, order_id)

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "order_not_found", "message": f"Orden {order_id} no encontrada"},
            )

        # Construir respuesta estructurada
        response = {
            "order_id": order.order_id,
            "customer": {
                "customer_id": order.customer.customer_id,
                "full_name": order.customer.full_name,
                "phone": order.customer.phone,
                "email": order.customer.email,
                "department": order.customer.department,
                "address": order.customer.address,
                "reference": order.customer.reference,
                "total_orders": order.customer.total_orders,
                "total_spent_bob": float(order.customer.total_spent_bob),
            },
            "total": float(order.total),
            "is_priority_shipping": order.is_priority_shipping,
            "priority_shipping_cost": float(order.priority_shipping_cost) if order.priority_shipping_cost else 0.0,
            "carrier_id": order.carrier_id,
            "delivery_cost": float(order.delivery_cost) if order.delivery_cost else 0.0,
            "return_cost": float(order.return_cost) if order.return_cost else 0.0,
            "current_status": order.tracking.order_status if order.tracking else "unknown",
            "tracking_code": order.tracking.tracking_code if order.tracking else None,
            "items": [
                {
                    "order_item_id": item.order_item_id,
                    "product_variant_id": item.product_variant_id,
                    "product_name": item.product_name,
                    "sku": item.product_variant.sku if item.product_variant else None,
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price),
                    "subtotal": float(item.subtotal),
                }
                for item in order.order_items
            ],
            "utm_source": order.utm_source,
            "utm_medium": order.utm_medium,
            "utm_campaign": order.utm_campaign,
            "utm_content": order.utm_content,
            "utm_term": order.utm_term,
            "external_order_id": order.external_order_id,
            "notes": order.notes,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        }

        return response

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)},
        )
