"""
PurchaseService - Gestión de compras a proveedores

REEMPLAZA TRIGGERS:
- product.fn_create_movement_from_purchase
- product.fn_recalculate_purchase_totals
- product.fn_create_transaction_from_purchase
- product.fn_resolve_supplier
- product.fn_resolve_payment_account
"""

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional, Dict, Tuple
from decimal import Decimal
from datetime import datetime
import logging

from app.models import Purchases, PurchaseItems, Suppliers, FinancialTransactions
from app.services.id_generator import IDGenerator
from app.services.inventory_service import InventoryService

logger = logging.getLogger(__name__)


class PurchaseService:
    """Service para gestión de compras a proveedores"""

    @staticmethod
    def create_full_purchase(
        db: Session,
        supplier_name: str,
        purchase_date: datetime,
        items: List[Dict],
        currency: str = "BOB",
        payment_account_id: Optional[str] = None,
        notes: Optional[str] = None
    ):
        """
        Crear compra completa con items, movimientos de inventario y transacción financiera

        Args:
            items: [{"variant_id": "PRD-1", "department": "LA_PAZ", "quantity": 10, "unit_cost": 50}]
        """
        try:
            supplier = PurchaseService.find_or_create_supplier(db, supplier_name, currency)
            purchase_id = IDGenerator.generate_purchase_id(db)

            total_quantity = 0
            total_cost = Decimal('0')
            for item in items:
                quantity = item['quantity']
                unit_cost = Decimal(str(item['unit_cost']))
                subtotal = quantity * unit_cost
                total_quantity += quantity
                total_cost += subtotal

            purchase = Purchases(
                purchase_id=purchase_id,
                supplier_id=supplier.supplier_id,
                purchase_date=purchase_date,
                total_cost=total_cost,
                total_quantity=total_quantity,
                currency=currency,
                payment_account_id=payment_account_id,
                notes=notes,
                status='received'
            )
            db.add(purchase)
            db.flush()

            logger.info(f"Purchase creado: {purchase_id} (supplier={supplier.supplier_id}, total={total_cost} {currency})")

            for item in items:
                quantity = item['quantity']
                unit_cost = Decimal(str(item['unit_cost']))
                subtotal = quantity * unit_cost

                purchase_item = PurchaseItems(
                    purchase_id=purchase_id,
                    product_variant_id=item['variant_id'],
                    department=item['department'],
                    quantity=quantity,
                    unit_cost=unit_cost,
                    subtotal=subtotal
                )
                db.add(purchase_item)

                InventoryService.create_movement(
                    db=db,
                    variant_id=item['variant_id'],
                    department=item['department'],
                    movement_type='purchase',
                    quantity=quantity,
                    reference_type='purchase',
                    reference_id=purchase_id,
                    notes=f"Compra de inventario - {quantity} unidades"
                )

            logger.info(f"{len(items)} items creados y sincronizados con inventario")

            if payment_account_id:
                PurchaseService._create_financial_transaction(
                    db=db,
                    purchase_id=purchase_id,
                    payment_account_id=payment_account_id,
                    total_cost=total_cost,
                    currency=currency,
                    purchase_date=purchase_date
                )
            else:
                logger.info(f"Purchase {purchase_id} sin payment_account_id. Transacción financiera NO creada.")

            db.commit()
            return purchase

        except Exception as e:
            db.rollback()
            logger.error(f"Error creando purchase: {str(e)}")
            raise ValueError(f"Error creando purchase: {str(e)}")

    @staticmethod
    def recalculate_purchase_totals(db: Session, purchase_id: str) -> Tuple[int, Decimal]:
        """Recalcular totales de purchase desde items"""
        result = db.query(
            func.coalesce(func.sum(PurchaseItems.quantity), 0).label('total_quantity'),
            func.coalesce(func.sum(PurchaseItems.subtotal), 0).label('total_cost')
        ).filter(
            PurchaseItems.purchase_id == purchase_id
        ).first()

        total_quantity = int(result.total_quantity)
        total_cost = Decimal(str(result.total_cost))

        purchase = db.query(Purchases).filter(
            Purchases.purchase_id == purchase_id
        ).first()

        if purchase:
            purchase.total_quantity = total_quantity
            purchase.total_cost = total_cost
            db.flush()
            logger.info(f"Totales recalculados para purchase {purchase_id}: qty={total_quantity}, cost={total_cost}")

        return (total_quantity, total_cost)

    @staticmethod
    def find_or_create_supplier(db: Session, supplier_name: str, default_currency: str = "BOB"):
        """Buscar o crear supplier por nombre"""
        supplier = db.query(Suppliers).filter(
            func.lower(Suppliers.supplier_name) == supplier_name.lower()
        ).first()

        if supplier:
            logger.info(f"Supplier encontrado: {supplier.supplier_id} ({supplier_name})")
            return supplier

        supplier_id = IDGenerator.generate_supplier_id(db)
        supplier = Suppliers(
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            default_currency=default_currency,
            is_active=True,
            contacts={},
            bank_accounts={}
        )
        db.add(supplier)
        db.flush()
        logger.info(f"Supplier creado: {supplier_id} ({supplier_name})")
        return supplier

    @staticmethod
    def _create_financial_transaction(
        db: Session,
        purchase_id: str,
        payment_account_id: str,
        total_cost: Decimal,
        currency: str,
        purchase_date: datetime
    ):
        """Crear transacción financiera para purchase (egreso)"""
        transaction_id = IDGenerator.generate_transaction_id(db)
        transaction = FinancialTransactions(
            transaction_id=transaction_id,
            transaction_type='expense',
            from_account_id=payment_account_id,
            amount=-total_cost,
            currency=currency,
            reference_type='purchase',
            reference_id=purchase_id,
            description=f"Pago compra {purchase_id}",
            transaction_date=purchase_date
        )
        db.add(transaction)
        db.flush()
        logger.info(f"Transacción financiera creada: -{total_cost} {currency} de cuenta {payment_account_id}")

    @staticmethod
    def get_purchase(db: Session, purchase_id: str):
        """Obtener purchase por ID con relaciones cargadas"""
        return db.query(Purchases).filter(
            Purchases.purchase_id == purchase_id
        ).options(
            joinedload(Purchases.supplier),
            joinedload(Purchases.purchase_items)
        ).first()

    @staticmethod
    def get_supplier_purchases(db: Session, supplier_id: str):
        """Obtener todas las compras de un proveedor"""
        return db.query(Purchases).filter(
            Purchases.supplier_id == supplier_id
        ).all()

    # ==================== VALIDACIÓN DE PRECIOS ====================

    @staticmethod
    def validate_purchase_price_changes(
        db: Session,
        product_variant_id: str,
        new_unit_price: Decimal,
        threshold_percent: float = 100.0
    ) -> dict:
        """
        Validar cambios de precio de compra y alertar si superan umbral

        VALIDACIÓN CRÍTICA:
        - Compara nuevo precio con último precio de compra
        - Alerta si cambio > threshold_percent (default: 100%)
        - Ejemplo: Si precio anterior era 100 BOB y nuevo es 250 BOB → +150% cambio → ALERTA

        Args:
            db: Database session
            product_variant_id: ID de la variante
            new_unit_price: Nuevo precio unitario propuesto
            threshold_percent: Umbral de cambio porcentual (default: 100%)

        Returns:
            Dict con validación y alerta si aplica
        """
        # Obtener último precio de compra de esta variante
        last_purchase_item = db.query(PurchaseItems).join(
            Purchases
        ).filter(
            PurchaseItems.product_variant_id == product_variant_id
        ).order_by(
            Purchases.purchase_date.desc()
        ).first()

        if not last_purchase_item:
            # No hay compras anteriores, no hay con qué comparar
            logger.info(
                f"✅ Primera compra de variante {product_variant_id}, "
                f"precio: {new_unit_price} BOB (sin validación previa)"
            )
            return {
                'variant_id': product_variant_id,
                'new_price': float(new_unit_price),
                'last_price': None,
                'price_change': None,
                'price_change_percent': None,
                'alert': False,
                'message': 'Primera compra de esta variante, no hay precio anterior para comparar'
            }

        # Calcular cambio de precio
        last_price = last_purchase_item.unit_cost
        price_change = new_unit_price - last_price
        price_change_percent = (price_change / last_price * 100) if last_price > 0 else 0

        # Verificar si supera umbral
        alert = abs(price_change_percent) > threshold_percent

        result = {
            'variant_id': product_variant_id,
            'new_price': float(new_unit_price),
            'last_price': float(last_price),
            'price_change': float(price_change),
            'price_change_percent': round(float(price_change_percent), 2),
            'threshold_percent': threshold_percent,
            'alert': alert,
            'alert_level': 'CRITICAL' if abs(price_change_percent) > 200 else ('HIGH' if alert else 'NORMAL'),
            'last_purchase_date': last_purchase_item.purchase.purchase_date.isoformat() if last_purchase_item.purchase else None
        }

        if alert:
            logger.warning(
                f"⚠️ ALERTA DE PRECIO: Variante {product_variant_id} - "
                f"Cambio de {last_price} → {new_unit_price} BOB "
                f"({price_change_percent:+.1f}%) SUPERA UMBRAL ({threshold_percent}%)"
            )
            result['message'] = (
                f"ALERTA: Precio cambió {price_change_percent:+.1f}% "
                f"(de {last_price} a {new_unit_price} BOB). "
                f"Verificar con proveedor antes de confirmar compra."
            )
        else:
            logger.info(
                f"✅ Precio de compra OK: Variante {product_variant_id} - "
                f"Cambio de {last_price} → {new_unit_price} BOB "
                f"({price_change_percent:+.1f}%)"
            )
            result['message'] = f"Cambio de precio dentro del umbral permitido ({threshold_percent}%)"

        return result

    @staticmethod
    def get_purchase_price_history(
        db: Session,
        product_variant_id: str,
        limit: int = 10
    ) -> list[dict]:
        """
        Obtener historial de precios de compra de una variante

        Args:
            db: Database session
            product_variant_id: ID de la variante
            limit: Número máximo de registros históricos

        Returns:
            Lista de precios históricos ordenados por fecha descendente
        """
        purchase_items = db.query(PurchaseItems).join(
            Purchases
        ).filter(
            PurchaseItems.product_variant_id == product_variant_id
        ).order_by(
            Purchases.purchase_date.desc()
        ).limit(limit).all()

        history = []
        for item in purchase_items:
            history.append({
                'purchase_id': item.purchase_id,
                'purchase_date': item.purchase.purchase_date.isoformat(),
                'unit_cost': float(item.unit_cost),
                'quantity': float(item.quantity),
                'currency': item.purchase.currency if item.purchase else 'BOB',
                'supplier_id': item.purchase.supplier_id if item.purchase else None
            })

        logger.info(
            f"📊 Historial de precios para variante {product_variant_id}: "
            f"{len(history)} registros encontrados"
        )

        return history
