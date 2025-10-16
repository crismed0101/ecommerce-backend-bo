-- Script para eliminar funciones redundantes (ya migradas a Python)
-- Las sequences se mantienen porque IDGenerator las usa

-- OPERATIONS: Funciones de generacion de IDs (migradas a IDGenerator)
DROP FUNCTION IF EXISTS operations.fn_generate_carrier_id() CASCADE;
DROP FUNCTION IF EXISTS operations.fn_generate_customer_id() CASCADE;
DROP FUNCTION IF EXISTS operations.fn_generate_order_id() CASCADE;
DROP FUNCTION IF EXISTS operations.fn_generate_order_item_id() CASCADE;
DROP FUNCTION IF EXISTS operations.fn_generate_payment_id() CASCADE;
DROP FUNCTION IF EXISTS operations.fn_generate_payment_order_id() CASCADE;
DROP FUNCTION IF EXISTS operations.fn_generate_rate_id() CASCADE;

-- OPERATIONS: Funciones de validacion (migradas a OrderService)
DROP FUNCTION IF EXISTS operations.fn_validate_customer_active() CASCADE;
DROP FUNCTION IF EXISTS operations.fn_validate_payment_carrier_active() CASCADE;
DROP FUNCTION IF EXISTS operations.fn_validate_carrier_deactivation() CASCADE;
DROP FUNCTION IF EXISTS operations.fn_validate_order_has_items() CASCADE;

-- OPERATIONS: Funciones de negocio (migradas a servicios)
DROP FUNCTION IF EXISTS operations.fn_auto_create_order_tracking() CASCADE;
DROP FUNCTION IF EXISTS operations.fn_update_customer_stats() CASCADE;
DROP FUNCTION IF EXISTS operations.fn_calculate_delivery_return_costs() CASCADE;
DROP FUNCTION IF EXISTS operations.fn_create_transaction_from_payment() CASCADE;
DROP FUNCTION IF EXISTS operations.fn_update_payment_from_order() CASCADE;

-- PRODUCT: Funciones de generacion de IDs (migradas a IDGenerator)
DROP FUNCTION IF EXISTS product.fn_generate_inventory_id() CASCADE;
DROP FUNCTION IF EXISTS product.fn_generate_movement_id() CASCADE;
DROP FUNCTION IF EXISTS product.fn_generate_product_id() CASCADE;
DROP FUNCTION IF EXISTS product.fn_generate_purchase_id() CASCADE;
DROP FUNCTION IF EXISTS product.fn_generate_supplier_id() CASCADE;
DROP FUNCTION IF EXISTS product.fn_generate_variant_id() CASCADE;
DROP FUNCTION IF EXISTS product.fn_generate_variant_id_sequential() CASCADE;

-- PRODUCT: Funciones de compras (migradas a PurchaseService)
DROP FUNCTION IF EXISTS product.fn_create_movement_from_purchase() CASCADE;
DROP FUNCTION IF EXISTS product.fn_recalculate_purchase_totals() CASCADE;
DROP FUNCTION IF EXISTS product.fn_create_transaction_from_purchase() CASCADE;
DROP FUNCTION IF EXISTS product.fn_resolve_supplier() CASCADE;
DROP FUNCTION IF EXISTS product.fn_resolve_payment_account() CASCADE;
DROP FUNCTION IF EXISTS product.fn_sync_purchase_to_inventory() CASCADE;
DROP FUNCTION IF EXISTS product.fn_update_inventory_from_purchase() CASCADE;

-- PRODUCT: Funciones de validacion (migradas a ProductService)
DROP FUNCTION IF EXISTS product.fn_deactivate_variants_on_product() CASCADE;
DROP FUNCTION IF EXISTS product.fn_validate_variant_active() CASCADE;
DROP FUNCTION IF EXISTS product.fn_validate_product_has_variants() CASCADE;

-- PRODUCT: Funciones de inventario (migradas a InventoryService)
DROP FUNCTION IF EXISTS product.fn_create_inventory_on_variant() CASCADE;
DROP FUNCTION IF EXISTS product.fn_manage_inventory_from_delivery() CASCADE;
DROP FUNCTION IF EXISTS product.fn_update_inventory_on_movement() CASCADE;
DROP FUNCTION IF EXISTS product.fn_recalculate_inventory_stock(character varying, product.department_stock) CASCADE;
DROP FUNCTION IF EXISTS product.fn_validate_movement_before_insert() CASCADE;
DROP FUNCTION IF EXISTS product.fn_validate_sufficient_stock() CASCADE;

-- FINANCE: Funciones de generacion de IDs (migradas a IDGenerator)
DROP FUNCTION IF EXISTS finance.fn_generate_account_id() CASCADE;
DROP FUNCTION IF EXISTS finance.fn_generate_transaction_id() CASCADE;
DROP FUNCTION IF EXISTS finance.fn_generate_lot_id() CASCADE;
DROP FUNCTION IF EXISTS finance.fn_generate_consumption_id() CASCADE;
DROP FUNCTION IF EXISTS finance.fn_generate_id(character varying, character varying) CASCADE;

-- FINANCE: Funciones de negocio (migradas a FinanceService)
DROP FUNCTION IF EXISTS finance.fn_update_balances() CASCADE;
DROP FUNCTION IF EXISTS finance.fn_validate_currencies() CASCADE;
DROP FUNCTION IF EXISTS finance.fn_validate_sufficient_balance() CASCADE;
DROP FUNCTION IF EXISTS finance.fn_consume_lots_fifo() CASCADE;
DROP FUNCTION IF EXISTS finance.fn_consumir_lotes_fifo(character varying, finance.currency_code, numeric, character varying) CASCADE;
DROP FUNCTION IF EXISTS finance.fn_create_currency_lot() CASCADE;
DROP FUNCTION IF EXISTS finance.fn_recalcular_cantidad_restante_de_lote(character varying) CASCADE;
DROP FUNCTION IF EXISTS finance.fn_trigger_recalcular_lote_tras_consumo() CASCADE;
DROP FUNCTION IF EXISTS finance.fn_validate_lot_consistency() CASCADE;
DROP FUNCTION IF EXISTS finance.fn_recalculate_account_balance(character varying) CASCADE;

-- MARKETING: Funciones de generacion de IDs (migradas a IDGenerator)
DROP FUNCTION IF EXISTS marketing.fn_generate_ad_account_id() CASCADE;
DROP FUNCTION IF EXISTS marketing.fn_generate_ad_id() CASCADE;
DROP FUNCTION IF EXISTS marketing.fn_generate_ad_metric_id() CASCADE;
DROP FUNCTION IF EXISTS marketing.fn_generate_adset_id() CASCADE;
DROP FUNCTION IF EXISTS marketing.fn_generate_breakdown_id() CASCADE;
DROP FUNCTION IF EXISTS marketing.fn_generate_campaign_id() CASCADE;
DROP FUNCTION IF EXISTS marketing.fn_generate_metric_id() CASCADE;
DROP FUNCTION IF EXISTS marketing.fn_generate_version_id() CASCADE;

-- MARKETING: Funciones de negocio (migradas a MarketingService)
DROP FUNCTION IF EXISTS marketing.fn_create_transaction_from_ads() CASCADE;
DROP FUNCTION IF EXISTS marketing.fn_close_previous_version() CASCADE;
DROP FUNCTION IF EXISTS marketing.fn_generate_version_number() CASCADE;
DROP FUNCTION IF EXISTS marketing.fn_update_timestamp() CASCADE;

-- NOTA: Las funciones fn_get_active_carrier_rates se mantienen porque pueden ser utiles para consultas
