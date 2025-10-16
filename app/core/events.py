"""
SQLAlchemy Event Listeners

REEMPLAZA: Todos los triggers de timestamp (fn_update_timestamp)

Principios:
- DRY: Un solo lugar para manejar timestamps
- CONVENTION OVER CONFIGURATION: Se aplica automáticamente a todos los modelos
- SEPARATION OF CONCERNS: Timestamps se manejan de forma centralizada

TRIGGERS REEMPLAZADOS:
- fn_update_timestamp (aplicado a ~25 tablas diferentes)
- Se ejecuta BEFORE UPDATE en todas las tablas con columna `updated_at`
"""

from sqlalchemy import event
from sqlalchemy.orm import Session
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def setup_timestamp_listeners():
    """
    Configurar event listeners para timestamps automáticos

    Se ejecuta una sola vez al iniciar la aplicación
    Aplica a TODOS los modelos que tengan columna `updated_at`

    REEMPLAZA:
    - operations.trg_00_customers_update_timestamp
    - operations.trg_00_carriers_update_timestamp
    - operations.trg_00_orders_update_timestamp
    - operations.trg_00_order_items_update_timestamp
    - operations.trg_00_order_tracking_update_timestamp
    - operations.trg_00_payments_update_timestamp
    - operations.trg_00_carrier_rates_update_timestamp
    - product.trg_00_products_update_timestamp
    - product.trg_00_variants_update_timestamp
    - product.trg_movements_update_timestamp
    - product.trg_00_purchases_update_timestamp
    - product.trg_00_suppliers_update_timestamp
    - finance.trg_00_accounts_update_timestamp
    - marketing.trg_00_ad_accounts_update_timestamp
    - marketing.trg_99_ads_updated_at
    - marketing.trg_99_metrics_updated_at
    - marketing.trg_00_ad_metrics_update_timestamp

    Y TODOS los demás triggers de timestamp
    """

    @event.listens_for(Session, 'before_flush')
    def receive_before_flush(session, flush_context, instances):
        """
        Event listener que se ejecuta ANTES de FLUSH en la sesión

        Si los objetos tienen columna `updated_at`, la actualiza automáticamente
        """
        for obj in session.dirty:
            # Verificar si el objeto tiene columna 'updated_at'
            if hasattr(obj, 'updated_at'):
                obj.updated_at = datetime.now()

                # Log solo en debug (opcional)
                # logger.debug(f"Timestamp actualizado: {obj.__class__.__name__}")

    logger.info("OK - Timestamp event listeners configurados para TODOS los modelos")


def setup_all_events():
    """
    Configurar TODOS los event listeners de la aplicación

    Llamar desde app/main.py al iniciar la aplicación
    """
    setup_timestamp_listeners()
    # Aquí se pueden agregar más event listeners en el futuro
    # setup_validation_listeners()
    # setup_audit_listeners()
    # etc.
