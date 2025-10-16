"""
Módulo de modelos ORM del sistema ecommerce_bo.

IMPORTANTE: Algunos modelos están definidos en múltiples archivos _generated.py
debido a relaciones cross-schema que genera sqlacodegen. Para evitar conflictos,
cada modelo se importa SOLO desde su schema "dueño".

Schemas y sus modelos:
- operations: Carriers, Customers, Orders, OrderItems, OrderTracking, CarrierRates, Payments, PaymentOrders
- product: Products, ProductVariants, Suppliers, Purchases, PurchaseItems, Inventory, InventoryMovements
- finance: Accounts, FinancialTransactions, CurrencyLots, TransactionLotConsumption
- marketing: AdAccounts, Campaigns, AdSets, Ads, AdCreativeVersions, AdDailyMetrics, etc.

Nota: Para regenerar modelos, ejecutar: python generate_models.py
"""

# ==============================================================================
# SCHEMA: OPERATIONS (dueño de Carriers, Customers, Orders)
# ==============================================================================

from app.models.operations_generated import (
    # Transportistas y tarifas
    Carriers,
    CarrierRates,
    
    # Clientes  
    Customers,
    
    # Órdenes
    Orders,
    OrderItems,
    OrderTracking,
    
    # Pagos COD
    Payments,
    PaymentOrders,
)

# ==============================================================================
# SCHEMA: PRODUCT (dueño de Products, ProductVariants)
# ==============================================================================

from app.models.product_generated import (
    # Catálogo
    Products,
    ProductVariants,
    
    # Proveedores y compras
    Suppliers,
    Purchases,
    PurchaseItems,
    
    # Inventario
    Inventory,
    InventoryMovements,
)

# ==============================================================================
# SCHEMA: FINANCE (dueño de Accounts)
# ==============================================================================

from app.models.finance_generated import (
    # Cuentas contables multi-moneda
    Accounts,
    
    # Transacciones financieras
    FinancialTransactions,
    
    # Sistema FIFO para moneda extranjera
    CurrencyLots,
    TransactionLotConsumption,
)

# ==============================================================================
# SCHEMA: MARKETING
# ==============================================================================

from app.models.marketing_generated import (
    # Configuración de ads
    AdAccounts,
    Campaigns,
    AdSets,
    Ads,
    AdCreativeVersions,
    
    # Métricas diarias
    AdDailyMetrics,
    AdDailyMetricsBreakdown,
    AdDailyMetricsOld,  # Tabla legacy
)

# ==============================================================================
# EXPORTACIONES
# ==============================================================================

__all__ = [
    # Operations
    "Carriers",
    "CarrierRates",
    "Customers",
    "Orders",
    "OrderItems",
    "OrderTracking",
    "Payments",
    "PaymentOrders",
    
    # Product
    "Products",
    "ProductVariants",
    "Suppliers",
    "Purchases",
    "PurchaseItems",
    "Inventory",
    "InventoryMovements",
    
    # Finance
    "Accounts",
    "FinancialTransactions",
    "CurrencyLots",
    "TransactionLotConsumption",
    
    # Marketing
    "AdAccounts",
    "Campaigns",
    "AdSets",
    "Ads",
    "AdCreativeVersions",
    "AdDailyMetrics",
    "AdDailyMetricsBreakdown",
    "AdDailyMetricsOld",
]
