"""
Service: Generación de IDs únicos

Principio: DRY - Un solo lugar para generar IDs
Usa sequences de PostgreSQL para garantizar unicidad
"""

from sqlalchemy.orm import Session
from sqlalchemy import text


class IDGenerator:
    """
    Generador de IDs con formato personalizado

    Formatos:
    - ORD00000001, ORD00000002, ...
    - CUS00000001, CUS00000002, ...
    - PRD00000001, PRD00000002, ...
    etc.
    """

    @staticmethod
    def _generate_id(db: Session, prefix: str, sequence_name: str) -> str:
        """
        Helper privado: Genera ID usando sequence de PostgreSQL

        Args:
            db: Database session
            prefix: Prefijo del ID (ej: "ORD", "CUS")
            sequence_name: Nombre de la sequence en PostgreSQL

        Returns:
            ID formateado (ej: "ORD00000123")
        """
        seq_value = db.execute(text(f"SELECT nextval('{sequence_name}')")).scalar()
        return f"{prefix}{seq_value:08d}"

    # ==================== OPERATIONS ====================

    @staticmethod
    def generate_customer_id(db: Session) -> str:
        """Genera CUS00000001"""
        return IDGenerator._generate_id(db, "CUS", "operations.seq_customer_id")

    @staticmethod
    def generate_order_id(db: Session) -> str:
        """Genera ORD00000001"""
        return IDGenerator._generate_id(db, "ORD", "operations.seq_order_id")

    @staticmethod
    def generate_order_item_id(db: Session, order_id: str, item_number: int) -> str:
        """
        Genera ORD00000001-1, ORD00000001-2, etc.

        Args:
            order_id: ID de la orden
            item_number: Número secuencial del item

        Returns:
            ID del item (ej: "ORD00000001-1")
        """
        return f"{order_id}-{item_number}"

    @staticmethod
    def generate_tracking_id(db: Session) -> str:
        """Genera TRCK00000001"""
        return IDGenerator._generate_id(db, "TRCK", "operations.seq_tracking_id")

    @staticmethod
    def generate_payment_id(db: Session) -> str:
        """Genera PAY00000001"""
        return IDGenerator._generate_id(db, "PAY", "operations.seq_payment_id")

    @staticmethod
    def generate_payment_order_id(db: Session) -> str:
        """Genera PORD00000001"""
        return IDGenerator._generate_id(db, "PORD", "operations.seq_payment_order_id")

    @staticmethod
    def generate_carrier_id(db: Session) -> str:
        """Genera CAR00000001"""
        return IDGenerator._generate_id(db, "CAR", "operations.seq_carrier_id")

    @staticmethod
    def generate_rate_id(db: Session) -> str:
        """Genera RATE00000001"""
        return IDGenerator._generate_id(db, "RATE", "operations.seq_rate_id")

    # ==================== PRODUCT ====================

    @staticmethod
    def generate_product_id(db: Session) -> str:
        """Genera PRD00000001"""
        return IDGenerator._generate_id(db, "PRD", "product.seq_product_id")

    @staticmethod
    def generate_variant_id(db: Session, product_id: str, variant_number: int) -> str:
        """
        Genera PRD00000001-1, PRD00000001-2, etc.

        Args:
            product_id: ID del producto
            variant_number: Número secuencial de la variante

        Returns:
            ID de la variante (ej: "PRD00000001-1")
        """
        return f"{product_id}-{variant_number}"

    @staticmethod
    def generate_inventory_id(db: Session) -> str:
        """Genera INV00000001"""
        return IDGenerator._generate_id(db, "INV", "product.seq_inventory_id")

    @staticmethod
    def generate_movement_id(db: Session) -> str:
        """Genera MOV00000001"""
        return IDGenerator._generate_id(db, "MOV", "product.seq_movement_id")

    @staticmethod
    def generate_purchase_id(db: Session) -> str:
        """Genera PURCH00000001"""
        return IDGenerator._generate_id(db, "PURCH", "product.seq_purchase_id")

    @staticmethod
    def generate_supplier_id(db: Session) -> str:
        """Genera SUP00000001"""
        return IDGenerator._generate_id(db, "SUP", "product.seq_supplier_id")

    # ==================== FINANCE ====================

    @staticmethod
    def generate_transaction_id(db: Session) -> str:
        """Genera TXN00000001 (transacciones financieras)"""
        return IDGenerator._generate_id(db, "TXN", "finance.seq_transaction_id")

    @staticmethod
    def generate_account_id(db: Session) -> str:
        """Genera ACC00000001 (cuentas/wallets)"""
        return IDGenerator._generate_id(db, "ACC", "finance.seq_account_id")

    @staticmethod
    def generate_consumption_id(db: Session) -> str:
        """Genera CONS00000001 (consumos financieros)"""
        return IDGenerator._generate_id(db, "CONS", "finance.seq_consumption_id")

    @staticmethod
    def generate_lot_id(db: Session) -> str:
        """Genera LOT00000001 (lotes de productos)"""
        return IDGenerator._generate_id(db, "LOT", "finance.seq_lot_id")

    # ==================== MARKETING ====================

    @staticmethod
    def generate_campaign_id(db: Session) -> str:
        """Genera CAMP00000001 (campañas de marketing)"""
        return IDGenerator._generate_id(db, "CAMP", "marketing.seq_campaign_id")

    @staticmethod
    def generate_adset_id(db: Session) -> str:
        """Genera ADSET00000001 (conjuntos de anuncios)"""
        return IDGenerator._generate_id(db, "ADSET", "marketing.seq_adset_id")

    @staticmethod
    def generate_ad_id(db: Session) -> str:
        """Genera AD00000001 (anuncios)"""
        return IDGenerator._generate_id(db, "AD", "marketing.seq_ad_id")

    @staticmethod
    def generate_ad_account_id(db: Session) -> str:
        """Genera ADACC00000001 (cuentas de anuncios)"""
        return IDGenerator._generate_id(db, "ADACC", "marketing.seq_ad_account_id")

    @staticmethod
    def generate_metric_id(db: Session) -> str:
        """Genera METR00000001 (métricas)"""
        return IDGenerator._generate_id(db, "METR", "marketing.seq_metric_id")

    @staticmethod
    def generate_ad_metric_id(db: Session) -> str:
        """Genera ADMETR00000001 (métricas de anuncios)"""
        return IDGenerator._generate_id(db, "ADMETR", "marketing.seq_ad_metric_id")

    @staticmethod
    def generate_breakdown_id(db: Session) -> str:
        """Genera BREAK00000001 (desgloses de métricas)"""
        return IDGenerator._generate_id(db, "BREAK", "marketing.seq_breakdown_id")

    @staticmethod
    def generate_version_id(db: Session) -> str:
        """Genera VER00000001 (versiones de anuncios)"""
        return IDGenerator._generate_id(db, "VER", "marketing.seq_version_id")
