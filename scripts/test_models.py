#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de prueba para verificar que los modelos ORM funcionan correctamente
"""
import sys

print("[*] Test de Modelos ORM")
print("=" * 60)

# 1. Test de imports
print("\n[1] Probando imports de modelos...")
try:
    from app.models import (
        # Operations
        Customers, Orders, OrderItems, OrderTracking,
        Carriers, CarrierRates,
        Payments, PaymentOrders,
        
        # Product
        Products, ProductVariants,
        Suppliers, Purchases, PurchaseItems,
        Inventory, InventoryMovements,
        
        # Finance
        Accounts, FinancialTransactions,
        CurrencyLots, TransactionLotConsumption,
        
        # Marketing
        AdAccounts, Campaigns, AdSets, Ads,
    )
    print("[OK] Todos los modelos importados correctamente!")
except Exception as e:
    print(f"[ERROR] Error importando modelos: {e}")
    sys.exit(1)

# 2. Test de conexión a BD
print("\n[2] Probando conexión a base de datos...")
try:
    from app.core.database import SessionLocal
    db = SessionLocal()
    print("[OK] Conexión a BD establecida!")
except Exception as e:
    print(f"[ERROR] Error conectando a BD: {e}")
    sys.exit(1)

# 3. Test de queries básicas
print("\n[3] Probando queries básicas...")
try:
    # Contar customers
    customer_count = db.query(Customers).count()
    print(f"[OK] Customers en BD: {customer_count}")
    
    # Contar productos
    product_count = db.query(Products).count()
    print(f"[OK] Products en BD: {product_count}")
    
    # Contar órdenes
    order_count = db.query(Orders).count()
    print(f"[OK] Orders en BD: {order_count}")
    
    print("\n[OK] Todas las queries funcionan correctamente!")
    
except Exception as e:
    print(f"[ERROR] Error en queries: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    db.close()

print("\n" + "=" * 60)
print("[OK] ¡Todos los tests pasaron exitosamente!")
print("=" * 60)
