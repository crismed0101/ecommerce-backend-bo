"""
Router: PRODUCTS

Endpoints para gestión de productos y variantes

Características:
- Actualización de precios con historial
- Alertas de cambios de precio
- Productos relacionados
- Recomendaciones de upsell/cross-sell
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.exceptions import BaseAppException
from app.schemas.product import (
    VariantPriceUpdateRequest,
    VariantPriceUpdateResponse,
    PriceChangeAlertsResponse,
    PriceChangeAlert,
    RelatedProductsResponse,
    RelatedProduct,
    AddRelatedProductRequest,
    AddRelatedProductResponse,
    ProductRecommendationsResponse,
    RecommendedProduct,
    RecommendationTypeEnum,
)
from app.services.product_service import ProductService

router = APIRouter(prefix="/api/v1/products", tags=["Products"])


@router.patch(
    "/variants/{variant_id}/price",
    response_model=VariantPriceUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="Actualizar precio de variante con historial",
    description="""
    Actualizar precio de venta de una variante de producto

    CARACTERÍSTICAS:
    - Mantiene historial completo de cambios de precio
    - Auditoría: reason opcional para justificar el cambio
    - Calcula cambio porcentual automáticamente
    - Actualiza precio efectivo inmediatamente

    **Caso de uso:**
    - Ajustes de precio por temporada
    - Promociones o descuentos
    - Correcciones de precio
    - Ajustes por inflación
    """,
)
def update_variant_price(
    variant_id: str,
    price_update: VariantPriceUpdateRequest,
    db: Session = Depends(get_db),
) -> VariantPriceUpdateResponse:
    """
    Actualizar precio de variante

    **Ejemplo:**
    ```json
    {
      "new_price": 180.00,
      "reason": "Ajuste por inflación - Octubre 2025"
    }
    ```
    """
    try:
        result = ProductService.update_variant_price(
            db=db,
            variant_id=variant_id,
            new_price=price_update.new_price,
            reason=price_update.reason
        )

        return VariantPriceUpdateResponse(
            success=True,
            variant_id=result['variant_id'],
            product_name=result.get('product_name'),
            sku=result.get('sku'),
            old_price=result['old_price'],
            new_price=result['new_price'],
            price_change=result['price_change'],
            price_change_percent=result['price_change_percent'],
            effective_date=result['effective_date'],
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


@router.get(
    "/alerts/price-changes",
    response_model=PriceChangeAlertsResponse,
    summary="Obtener alertas de cambios de precio recientes",
    description="""
    Listar cambios de precio significativos en un período

    ALERTAS:
    - MAJOR_INCREASE: Aumento > 20%
    - MAJOR_DECREASE: Reducción > 20%
    - NORMAL: Cambio < 20%

    **Parámetro:**
    - days: Período a analizar (default: 7 días)

    **Caso de uso:**
    - Dashboard de monitoreo de precios
    - Auditoría de cambios de precio
    - Detección de errores en actualizaciones masivas
    """,
)
def get_price_change_alerts(
    days: int = Query(7, ge=1, le=90, description="Período en días (default: 7)"),
    db: Session = Depends(get_db),
) -> PriceChangeAlertsResponse:
    """
    Obtener alertas de cambios de precio

    **Ejemplos de uso:**

    ```
    # Cambios últimos 7 días
    GET /api/v1/products/alerts/price-changes

    # Cambios últimos 30 días
    GET /api/v1/products/alerts/price-changes?days=30
    ```
    """
    try:
        result = ProductService.get_price_change_alerts(
            db=db,
            days=days,
            threshold_percent=20.0
        )

        alerts = []
        major_increases = 0
        major_decreases = 0

        for alert in result['alerts']:
            alert_level = alert['alert_level']
            if alert_level == 'MAJOR_INCREASE':
                major_increases += 1
            elif alert_level == 'MAJOR_DECREASE':
                major_decreases += 1

            alerts.append(PriceChangeAlert(
                variant_id=alert['variant_id'],
                product_name=alert.get('product_name'),
                sku=alert.get('sku'),
                old_price=alert['old_price'],
                new_price=alert['new_price'],
                price_change=alert['price_change'],
                price_change_percent=alert['price_change_percent'],
                change_date=alert['change_date'],
                alert_level=alert_level
            ))

        return PriceChangeAlertsResponse(
            success=True,
            days=days,
            total_changes=result['total_changes'],
            major_increases=major_increases,
            major_decreases=major_decreases,
            alerts=alerts
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)},
        )


@router.get(
    "/{product_id}/related",
    response_model=RelatedProductsResponse,
    summary="Obtener productos relacionados",
    description="""
    Listar productos relacionados para upsell y cross-sell

    TIPOS:
    - upsell: Productos de mayor valor en la misma categoría
    - cross_sell: Productos complementarios

    **Caso de uso:**
    - Mostrar "Productos relacionados" en página de producto
    - Sugerencias de "También te puede interesar"
    - Aumentar ticket promedio
    """,
)
def get_related_products(
    product_id: str,
    db: Session = Depends(get_db),
) -> RelatedProductsResponse:
    """
    Obtener productos relacionados

    **Ejemplo de uso:**

    ```
    GET /api/v1/products/PRD00000001/related
    ```
    """
    try:
        related = ProductService.get_related_products(
            db=db,
            product_id=product_id
        )

        related_items = []
        for item in related:
            related_items.append(RelatedProduct(
                product_id=item['related_product_id'],
                product_name=item['product_name'],
                category=item.get('category'),
                recommendation_type=item['recommendation_type'],
                priority=item['priority']
            ))

        # Obtener nombre del producto principal
        from app.models import Products
        product = db.query(Products).filter(Products.product_id == product_id).first()
        product_name = product.product_name if product else None

        return RelatedProductsResponse(
            success=True,
            product_id=product_id,
            product_name=product_name,
            total_related=len(related_items),
            related_products=related_items
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)},
        )


@router.post(
    "/{product_id}/related",
    response_model=AddRelatedProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar producto relacionado",
    description="""
    Agregar un producto relacionado para upsell o cross-sell

    CARACTERÍSTICAS:
    - Define tipo de recomendación (upsell o cross_sell)
    - Prioridad configurable (1=más alta, 10=más baja)
    - Evita duplicados automáticamente

    **Ejemplo de uso:**
    - Relacionar "Funda de celular" con "Celular" (cross-sell)
    - Relacionar "iPhone 15 Pro" con "iPhone 15" (upsell)
    """,
)
def add_related_product(
    product_id: str,
    related: AddRelatedProductRequest,
    db: Session = Depends(get_db),
) -> AddRelatedProductResponse:
    """
    Agregar producto relacionado

    **Ejemplo:**
    ```json
    {
      "related_product_id": "PRD00000002",
      "recommendation_type": "cross_sell",
      "priority": 1
    }
    ```
    """
    try:
        result = ProductService.add_related_product(
            db=db,
            product_id=product_id,
            related_product_id=related.related_product_id,
            recommendation_type=related.recommendation_type.value,
            priority=related.priority
        )

        return AddRelatedProductResponse(
            success=True,
            product_id=result['product_id'],
            related_product_id=result['related_product_id'],
            recommendation_type=result['recommendation_type'],
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
    "/{product_id}/recommendations",
    response_model=ProductRecommendationsResponse,
    summary="Obtener recomendaciones de productos (upsell/cross-sell)",
    description="""
    Obtener recomendaciones automáticas basadas en historial de ventas

    ALGORITMO:
    - Upsell: Productos comprados junto con éste de mayor valor
    - Cross-sell: Productos frecuentemente comprados juntos

    **Métricas:**
    - Recommendation score: Frecuencia de compra conjunta
    - Ordenados por score descendente

    **Caso de uso:**
    - Recomendaciones automáticas en checkout
    - "Los clientes que compraron esto también compraron..."
    - Optimización de revenue
    """,
)
def get_product_recommendations(
    product_id: str,
    recommendation_type: RecommendationTypeEnum = Query(
        RecommendationTypeEnum.UPSELL,
        description="Tipo de recomendación"
    ),
    limit: int = Query(5, ge=1, le=20, description="Número máximo de recomendaciones"),
    db: Session = Depends(get_db),
) -> ProductRecommendationsResponse:
    """
    Obtener recomendaciones de productos

    **Ejemplos de uso:**

    ```
    # Recomendaciones de upsell (top 5)
    GET /api/v1/products/PRD00000001/recommendations?recommendation_type=upsell

    # Recomendaciones de cross-sell (top 10)
    GET /api/v1/products/PRD00000001/recommendations?recommendation_type=cross_sell&limit=10
    ```
    """
    try:
        if recommendation_type == RecommendationTypeEnum.UPSELL:
            recommendations = ProductService.get_upsell_recommendations(
                db=db,
                product_id=product_id,
                limit=limit
            )
        else:  # CROSS_SELL
            recommendations = ProductService.get_cross_sell_recommendations(
                db=db,
                product_id=product_id,
                limit=limit
            )

        recommended_items = []
        for rec in recommendations:
            recommended_items.append(RecommendedProduct(
                product_id=rec['recommended_product_id'],
                product_name=rec['product_name'],
                category=rec.get('category'),
                avg_price=rec['avg_price'],
                recommendation_score=rec['recommendation_score'],
                recommendation_reason=rec['recommendation_reason']
            ))

        # Obtener nombre del producto principal
        from app.models import Products
        product = db.query(Products).filter(Products.product_id == product_id).first()
        product_name = product.product_name if product else None

        return ProductRecommendationsResponse(
            success=True,
            product_id=product_id,
            product_name=product_name,
            recommendation_type=recommendation_type.value,
            total_recommendations=len(recommended_items),
            recommendations=recommended_items
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)},
        )
