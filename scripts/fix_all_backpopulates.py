#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para eliminar TODOS los back_populates cross-schema problemáticos
"""
import re
from pathlib import Path

def fix_all_backpopulates(file_path):
    """
    Busca y elimina todos los back_populates que apuntan a modelos de otros schemas
    """
    print(f"\n[*] Procesando: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Definir modelos por schema
    schema_models = {
        'operations': ['Carriers', 'CarrierRates', 'Customers', 'Orders', 'OrderItems', 'OrderTracking', 'Payments', 'PaymentOrders'],
        'product': ['Products', 'ProductVariants', 'Suppliers', 'Purchases', 'PurchaseItems', 'Inventory', 'InventoryMovements'],
        'finance': ['Accounts', 'FinancialTransactions', 'CurrencyLots', 'TransactionLotConsumption'],
        'marketing': ['AdAccounts', 'Campaigns', 'AdSets', 'Ads', 'AdCreativeVersions', 'AdDailyMetrics', 'AdDailyMetricsBreakdown', 'AdDailyMetricsOld']
    }
    
    # Determinar qué schema es este archivo
    current_schema = None
    for schema in schema_models.keys():
        if f'{schema}_generated.py' in str(file_path):
            current_schema = schema
            break
    
    if not current_schema:
        print(f"    [SKIP] No se pudo determinar el schema")
        return
    
    # Modelos que pertenecen a este schema
    own_models = set(schema_models[current_schema])
    
    # Buscar todos los relationships
    pattern = r"(\w+):\s+Mapped\[[\w\[\]'\"]+\]\s+=\s+relationship\('(\w+)'[^)]*,\s*back_populates='(\w+)'"
    
    matches = list(re.finditer(pattern, content))
    
    if not matches:
        print(f"    [SKIP] No se encontraron relationships con back_populates")
        return
    
    modified = False
    for match in matches:
        attr_name, model_name, back_pop_name = match.groups()
        
        # Si el modelo apunta a otro schema, eliminar back_populates
        if model_name not in own_models:
            # Eliminar el back_populates
            old_text = match.group(0)
            new_text = re.sub(r",\s*back_populates='[^']*'", '', old_text)
            content = content.replace(old_text, new_text)
            print(f"    [OK] Eliminado back_populates de {attr_name} -> {model_name}")
            modified = True
    
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"    [OK] Archivo actualizado")
    else:
        print(f"    [INFO] No había back_populates cross-schema")

if __name__ == "__main__":
    print("="  * 70)
    print("ELIMINACIÓN AUTOMÁTICA DE BACK_POPULATES CROSS-SCHEMA")
    print("=" * 70)
    
    files = [
        Path('app/models/operations_generated.py'),
        Path('app/models/product_generated.py'),
        Path('app/models/finance_generated.py'),
        Path('app/models/marketing_generated.py')
    ]
    
    for file_path in files:
        if file_path.exists():
            fix_all_backpopulates(file_path)
    
    print("\n" + "=" * 70)
    print("[OK] Proceso completado!")
    print("=" * 70)
