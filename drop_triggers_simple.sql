-- Script para eliminar triggers redundantes
-- OPERATIONS
DROP TRIGGER IF EXISTS trg_00_customers_update_timestamp ON operations.customers CASCADE;
DROP TRIGGER IF EXISTS trg_00_carriers_update_timestamp ON operations.carriers CASCADE;
DROP TRIGGER IF EXISTS trg_00_orders_update_timestamp ON operations.orders CASCADE;
DROP TRIGGER IF EXISTS trg_00_order_items_update_timestamp ON operations.order_items CASCADE;
DROP TRIGGER IF EXISTS trg_00_order_tracking_update_timestamp ON operations.order_tracking CASCADE;
DROP TRIGGER IF EXISTS trg_00_payments_update_timestamp ON operations.payments CASCADE;
DROP TRIGGER IF EXISTS trg_00_carrier_rates_update_timestamp ON operations.carrier_rates CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_customer_id ON operations.customers CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_carrier_id ON operations.carriers CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_order_id ON operations.orders CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_payment_id ON operations.payments CASCADE;
DROP TRIGGER IF EXISTS trg_01_validate_customer ON operations.orders CASCADE;
DROP TRIGGER IF EXISTS trg_validate_payment_carrier_active ON operations.payments CASCADE;

-- PRODUCT
DROP TRIGGER IF EXISTS trg_00_products_update_timestamp ON product.products CASCADE;
DROP TRIGGER IF EXISTS trg_00_variants_update_timestamp ON product.product_variants CASCADE;
DROP TRIGGER IF EXISTS trg_movements_update_timestamp ON product.inventory_movements CASCADE;
DROP TRIGGER IF EXISTS trg_00_purchases_update_timestamp ON product.purchases CASCADE;
DROP TRIGGER IF EXISTS trg_00_suppliers_update_timestamp ON product.suppliers CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_product_id ON product.products CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_variant_id ON product.product_variants CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_inventory_id ON product.inventory CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_movement_id ON product.inventory_movements CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_purchase_id ON product.purchases CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_supplier_id ON product.suppliers CASCADE;
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
DROP TRIGGER IF EXISTS trg_01_deactivate_variants ON product.products CASCADE;
DROP TRIGGER IF EXISTS trg_01_validate_variant_active_insert ON product.product_variants CASCADE;
DROP TRIGGER IF EXISTS trg_01_validate_variant_active_update ON product.product_variants CASCADE;

-- FINANCE
DROP TRIGGER IF EXISTS trg_00_accounts_update_timestamp ON finance.accounts CASCADE;
DROP TRIGGER IF EXISTS trg_00_transactions_update_timestamp ON finance.transactions CASCADE;
DROP TRIGGER IF EXISTS trg_00_lots_update_timestamp ON finance.currency_lots CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_account_id ON finance.accounts CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_transaction_id ON finance.transactions CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_lot_id ON finance.currency_lots CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_consumption_id ON finance.lot_consumptions CASCADE;
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

-- MARKETING
DROP TRIGGER IF EXISTS trg_00_ad_accounts_update_timestamp ON marketing.ad_accounts CASCADE;
DROP TRIGGER IF EXISTS trg_99_ads_updated_at ON marketing.ads CASCADE;
DROP TRIGGER IF EXISTS trg_99_metrics_updated_at ON marketing.ad_metrics CASCADE;
DROP TRIGGER IF EXISTS trg_00_ad_metrics_update_timestamp ON marketing.ad_metrics CASCADE;
DROP TRIGGER IF EXISTS trg_00_campaigns_update_timestamp ON marketing.campaigns CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_ad_account_id ON marketing.ad_accounts CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_ad_id ON marketing.ads CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_metric_id ON marketing.ad_metrics CASCADE;
DROP TRIGGER IF EXISTS trg_00_generate_campaign_id ON marketing.campaigns CASCADE;
DROP TRIGGER IF EXISTS trg_create_transaction_from_ads_insert ON marketing.ads CASCADE;
DROP TRIGGER IF EXISTS trg_create_transaction_from_ads_update ON marketing.ads CASCADE;
DROP TRIGGER IF EXISTS trg_02_versions_close_previous ON marketing.ad_versions CASCADE;
DROP TRIGGER IF EXISTS trg_01_versions_generate_number ON marketing.ad_versions CASCADE;
