"""
Router: WEBHOOKS

Endpoints para recibir webhooks de plataformas externas (Shopify, etc.)

Principios:
- SEGURIDAD: Verificación HMAC obligatoria
- IDEMPOTENCY: No procesar webhooks duplicados
- ASYNC: Responder rápido (202 Accepted)
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status, Header
from sqlalchemy.orm import Session
import hmac
import hashlib
import logging
from typing import Optional

from app.core.database import get_db
from app.core.config import get_settings
from app.adapters.shopify_adapter import ShopifyAdapter
from app.services.order_service import OrderService
from app.schemas.order import OrderCreate

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# ==================== HELPERS ====================

def verify_shopify_hmac(
    body: bytes,
    hmac_header: Optional[str]
) -> bool:
    """
    Verificar firma HMAC de Shopify

    Shopify envía el HMAC en el header: X-Shopify-Hmac-SHA256

    Args:
        body: Raw request body (bytes)
        hmac_header: Valor del header X-Shopify-Hmac-SHA256

    Returns:
        True si válido, False si no
    """

    if not hmac_header:
        logger.warning("❌ HMAC header missing")
        return False

    # Obtener secret de Shopify desde config
    secret = settings.SHOPIFY_WEBHOOK_SECRET  # Debe estar en .env

    if not secret:
        logger.error("❌ SHOPIFY_WEBHOOK_SECRET no configurado")
        return False

    # Calcular HMAC esperado
    expected_hmac = hmac.new(
        secret.encode('utf-8'),
        body,
        hashlib.sha256
    ).hexdigest()

    # Comparar (timing-safe)
    is_valid = hmac.compare_digest(expected_hmac, hmac_header)

    if is_valid:
        logger.info("✅ HMAC válido")
    else:
        logger.warning(f"❌ HMAC inválido: expected={expected_hmac}, got={hmac_header}")

    return is_valid


# ==================== ENDPOINTS ====================

@router.post(
    "/shopify/orders/create",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Webhook de Shopify: Nueva orden",
    description="""
    Recibe webhook cuando se crea una orden en Shopify

    FLUJO:
    1. Verificar HMAC (seguridad)
    2. Transformar webhook con ShopifyAdapter
    3. Crear orden con OrderService
    4. Responder 202 Accepted (rápido)

    IDEMPOTENCY: Si la orden ya existe (external_order_id), retorna 202 sin error
    """
)
async def shopify_order_create(
    request: Request,
    db: Session = Depends(get_db),
    x_shopify_hmac_sha256: Optional[str] = Header(None)
):
    """
    Webhook de Shopify: orders/create

    Headers requeridos:
    - X-Shopify-Hmac-SHA256: Firma HMAC del payload

    IMPORTANTE:
    - Este endpoint debe ser PÚBLICO (sin autenticación)
    - Shopify lo llama directamente
    - La seguridad viene del HMAC
    """

    try:
        # PASO 1: Leer body raw (necesario para verificar HMAC)
        body = await request.body()

        logger.info(f"📨 Webhook recibido de Shopify: {len(body)} bytes")

        # PASO 2: Verificar HMAC (CRÍTICO)
        if not verify_shopify_hmac(body, x_shopify_hmac_sha256):
            logger.error("🚨 HMAC verification FAILED - Possible attack!")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid HMAC signature"
            )

        # PASO 3: Parsear JSON
        import json
        webhook_data = json.loads(body)

        shopify_order_id = webhook_data.get('id')
        logger.info(f"📦 Procesando Shopify order: {shopify_order_id}")

        # PASO 4: Transformar con ShopifyAdapter
        order_data_dict = ShopifyAdapter.transform_order(webhook_data)

        # Convertir dict a OrderCreate schema (validación Pydantic)
        order_data = OrderCreate(**order_data_dict)

        # PASO 5: Crear orden con OrderService
        result = OrderService.create_full_order(db, order_data)

        logger.info(f"✅ Orden procesada: {result.order_id} (Shopify: {shopify_order_id})")

        # PASO 6: Responder 202 Accepted
        return {
            "success": True,
            "message": "Webhook procesado correctamente",
            "order_id": result.order_id,
            "shopify_order_id": shopify_order_id,
            "products_created": result.products_created,
            "warnings": result.warnings
        }

    except HTTPException:
        # Re-raise HTTP exceptions (como 401)
        raise

    except Exception as e:
        logger.error(f"❌ Error procesando webhook: {str(e)}", exc_info=True)

        # NO devolver 500 (Shopify reintentaría infinitamente)
        # Devolver 202 pero loggear el error
        return {
            "success": False,
            "message": f"Error procesando webhook: {str(e)}",
            "shopify_order_id": webhook_data.get('id') if 'webhook_data' in locals() else None
        }


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Verificar que el servidor de webhooks está activo"
)
def webhook_health():
    """
    Health check para webhooks

    Shopify puede usar esto para verificar conectividad
    """
    return {
        "status": "ok",
        "service": "webhooks",
        "message": "Webhook server is running"
    }
