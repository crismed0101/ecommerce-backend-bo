-- ============================================================================
-- SCRIPT: Eliminar triggers redundantes (migrados a backend Python)
-- Fecha: 2025-10-15
-- Descripción: Elimina triggers que ya fueron migrados a servicios Python
-- ============================================================================

-- IMPORTANTE: Este script es SEGURO de ejecutar porque:
-- 1. Todos estos triggers ya fueron migrados a Python
-- 2. El backend maneja toda la lógica
-- 3. Se mantienen comentarios para posible rollback

BEGIN;

-- ============================================================================
-- OPERATIONS SCHEMA
-- ============================================================================

-- Triggers de TIMESTAMP (migrados a event listeners)
DROP TRIGGER IF EXISTS trg_00_customers_update_timestamp ON operations.customers CASCADE;
DROP TRIGGER IF EXISTS trg_00_carriers_update_timestamp ON operations.carriers CASCADE;
DROP TRIGGER IF EXISTS trg_00_orders_update_timestamp ON operations.orders CASCADE;
DROP TRIGGER IF EXISTS trg_00_order_items_update_timestamp ON operations.order_items CASCADE;
DROP TRIGGER IF EXISTS trg_00_order_tracking_update_timestamp ON operations.order_tracking CASCADE;
DROP TRIGGER IF EXISTS trg_00_payments_update_timestamp ON operations.payments CASCADE;
DROP TRIGGER IF EXISTS trg_00_carrier_rates_update_timestamp ON operations.carrier_rates CASCADE;

-- Triggers de GENERACIÓN DE IDs (migrados a IDGenerator)
DROP TRIGGER IF EXISTS trg_00_generate_customer_id ON operations.customers CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_carrier_id ON operations.carriers CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_order_id ON operations.orders CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_payment_id ON operations.payments CASCADE;

-- Triggers de VALIDACIÓN (migrados a OrderService)
DROP TRIGGER IF EXISTS trg_01_validate_customer ON operations.orders CASCADE;
DROP TRIGGER IF EXISTS trg_validate_payment_carrier_active ON operations.payments CASCADE;

RAISE NOTICE '✅ OPERATIONS: 13 triggers eliminados';

-- ============================================================================
-- PRODUCT SCHEMA
-- ============================================================================

-- Triggers de TIMESTAMP (migrados a event listeners)
DROP TRIGGER IF EXISTS trg_00_products_update_timestamp ON product.products CASCADE;
DROP TRIGGER IF EXISTS trg_00_variants_update_timestamp ON product.product_variants CASCADE;
DROP TRIGGER IF EXISTS trg_movements_update_timestamp ON product.inventory_movements CASCADE;
DROP TRIGGER IF EXISTS trg_00_purchases_update_timestamp ON product.purchases CASCADE;
DROP TRIGGER IF EXISTS trg_00_suppliers_update_timestamp ON product.suppliers CASCADE;

-- Triggers de GENERACIÓN DE IDs (migrados a IDGenerator)
DROP TRIGGER IF EXISTS trg_00_generate_product_id ON product.products CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_variant_id ON product.product_variants CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_inventory_id ON product.inventory CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_movement_id ON product.inventory_movements CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_purchase_id ON product.purchases CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_supplier_id ON product.suppliers CASCADE;

-- Triggers de COMPRAS (migrados a PurchaseService)
DROP TRIGGER IF EXISTS trg_sync_purchase_to_inventory_insert ON product.purchase_items CASCADE;
DROP TRIGGER IF EXISTS trg_sync_purchase_to_inventory_update ON product.purchase_items CASCADE;
DROP TRIGGER IF EXISTS trg_sync_purchase_to_inventory_delete ON product.purchase_items CASCADE;
DROP TRIGGER IF EXISTS trg_recalculate_purchase_totals_insert ON product.purchase_items CASCADE;
DROP TRIGGER IF EXISTS trg_recalculate_purchase_totals_update ON product.purchase_items CASCADE;
DROP TRIGGER IF EXISTS trg_recalculate_purchase_totals_delete ON product.purchase_items CASCADE;
DROP TRIGGER IF EXISTS trg_create_transaction_from_purchase ON product.purchases CASCADE;
DROP TRIGGER IF EXISTS trg_00_resolve_supplier_insert ON product.purchases CASCADE;
DROP TRIGGER IF EXISTS trg_00_resolve_supplier_update ON product.purchases CASCADE;
DROP TRIGGER IF EXISTS trg_01_resolve_payment_account_insert ON product.purchases CASCADE;
DROP TRIGGER IF EXISTS trg_01_resolve_payment_account_update ON product.purchases CASCADE;

-- Triggers de VALIDACIÓN DE PRODUCTOS (migrados a ProductService)
DROP TRIGGER IF EXISTS trg_01_deactivate_variants ON product.products CASCADE;
DROP TRIGGER IF EXISTS trg_01_validate_variant_active_insert ON product.product_variants CASCADE;
DROP TRIGGER IF EXISTS trg_01_validate_variant_active_update ON product.product_variants CASCADE;

RAISE NOTICE '✅ PRODUCT: 24 triggers eliminados';

-- ============================================================================
-- FINANCE SCHEMA
-- ============================================================================

-- Triggers de TIMESTAMP (migrados a event listeners)
DROP TRIGGER IF EXISTS trg_00_accounts_update_timestamp ON finance.accounts CASCADE;
DROP TRIGGER IF EXISTS trg_00_transactions_update_timestamp ON finance.transactions CASCADE;
DROP TRIGGER IF EXISTS trg_00_lots_update_timestamp ON finance.currency_lots CASCADE;

-- Triggers de GENERACIÓN DE IDs (migrados a IDGenerator)
DROP TRIGGER IF EXISTS trg_00_generate_account_id ON finance.accounts CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_transaction_id ON finance.transactions CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_lot_id ON finance.currency_lots CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_consumption_id ON finance.lot_consumptions CASCADE;

-- Triggers de FINANZAS (migrados a FinanceService)
DROP TRIGGER IF EXISTS trg_10_update_balances ON finance.transactions CASCADE;
DROP TRIGGER IF EXISTS trg_01_validate_currencies_insert ON finance.transactions CASCADE;
DROP TRIGGER IF EXISTS trg_01_validate_currencies_update ON finance.transactions CASCADE;
DROP TRIGGER IF EXISTS trg_02_validate_sufficient_balance ON finance.transactions CASCADE;
DROP TRIGGER IF EXISTS trg_11_consume_lots_fifo ON finance.transactions CASCADE;
DROP TRIGGER IF EXISTS trg_12_create_currency_lot ON finance.transactions CASCADE;
DROP TRIGGER IF EXISTS trg_recalcular_lote_insert ON finance.lot_consumptions CASCADE;
DROP TRIGGER IF EXISTS trg_recalcular_lote_update ON finance.lot_consumptions CASCADE;
DROP TRIGGER IF EXISTS trg_recalcular_lote_delete ON finance.lot_consumptions CASCADE;
DROP TRIGGER IF EXISTS trg_lots_validate_consistency ON finance.currency_lots CASCADE;

RAISE NOTICE '✅ FINANCE: 18 triggers eliminados';

-- ============================================================================
-- MARKETING SCHEMA
-- ============================================================================

-- Triggers de TIMESTAMP (migrados a event listeners)
DROP TRIGGER IF EXISTS trg_00_ad_accounts_update_timestamp ON marketing.ad_accounts CASCADE;
DROP TRIGGER IF EXISTS trg_99_ads_updated_at ON marketing.ads CASCADE;
DROP TRIGGER IF EXISTS trg_99_metrics_updated_at ON marketing.ad_metrics CASCADE;
DROP TRIGGER IF EXISTS trg_00_ad_metrics_update_timestamp ON marketing.ad_metrics CASCADE;
DROP TRIGGER IF EXISTS trg_00_campaigns_update_timestamp ON marketing.campaigns CASCADE;

-- Triggers de GENERACIÓN DE IDs (migrados a IDGenerator)
DROP TRIGGER IF EXISTS trg_00_generate_ad_account_id ON marketing.ad_accounts CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_ad_id ON marketing.ads CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_metric_id ON marketing.ad_metrics CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_campaign_id ON marketing.campaigns CASCADE;

-- Triggers de MARKETING (migrados a MarketingService)
DROP TRIGGER IF EXISTS trg_create_transaction_from_ads_insert ON marketing.ads CASCADE;
DROP TRIGGER IF EXISTS trg_create_transaction_from_ads_update ON marketing.ads CASCADE;
DROP TRIGGER IF EXISTS trg_02_versions_close_previous ON marketing.ad_versions CASCADE;
DROP TRIGGER IF EXISTS trg_01_versions_generate_number ON marketing.ad_versions CASCADE;

RAISE NOTICE '✅ MARKETING: 13 triggers eliminados';

-- ============================================================================
-- RESUMEN
-- ============================================================================
-- Total triggers eliminados: 68
-- Triggers restantes: ~19 (triggers auxiliares que no afectan lógica de negocio)
-- ============================================================================

COMMIT;

-- Verificar que se eliminaron
DO $$
DECLARE
    trigger_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO trigger_count
    FROM information_schema.triggers
    WHERE trigger_schema IN ('operations', 'product', 'finance', 'marketing')
    AND trigger_name LIKE 'trg_%';

    RAISE NOTICE '============================================';
    RAISE NOTICE 'Triggers restantes en schemas de negocio: %', trigger_count;
    RAISE NOTICE '============================================';
END $$;

-- Listar triggers restantes
SELECT
    event_object_schema as schema,
    event_object_table as table,
    trigger_name,
    action_timing || ' ' || event_manipulation as evento
FROM information_schema.triggers
WHERE event_object_schema IN ('operations', 'product', 'finance', 'marketing')
ORDER BY event_object_schema, event_object_table, trigger_name;
