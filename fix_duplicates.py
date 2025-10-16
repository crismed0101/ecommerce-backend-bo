#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para eliminar modelos duplicados y agregar imports cross-schema
"""
import re
from pathlib import Path

# Definir qué modelos pertenecen a cada schema (schema "dueño")
SCHEMA_OWNERS = {
    'finance': [
        'Accounts', 'FinancialTransactions', 'CurrencyLots', 
        'TransactionLotConsumption'
    ],
    'operations': [
        'Carriers', 'CarrierRates', 'Customers', 'Orders', 
        'OrderItems', 'OrderTracking', 'Payments', 'PaymentOrders'
    ],
    'product': [
        'Products', 'ProductVariants', 'Suppliers', 'Purchases', 
        'PurchaseItems', 'Inventory', 'InventoryMovements'
    ],
    'marketing': [
        'AdAccounts', 'Campaigns', 'AdSets', 'Ads', 'AdCreativeVersions',
        'AdDailyMetrics', 'AdDailyMetricsBreakdown', 'AdDailyMetricsOld'
    ]
}

def get_owner_schema(model_name):
    """Retorna el schema dueño de un modelo"""
    for schema, models in SCHEMA_OWNERS.items():
        if model_name in models:
            return schema
    return None

def extract_class_definition(content, class_name):
    """
    Extrae la definición completa de una clase (incluyendo su contenido)
    """
    # Buscar el inicio de la clase
    pattern = rf'class {class_name}\([^)]+\):'
    match = re.search(pattern, content)
    
    if not match:
        return None, None
    
    start_pos = match.start()
    
    # Encontrar el final de la clase (siguiente clase o final del archivo)
    next_class_pattern = r'\nclass [A-Z]'
    next_match = re.search(next_class_pattern, content[start_pos + 1:])
    
    if next_match:
        end_pos = start_pos + 1 + next_match.start()
    else:
        end_pos = len(content)
    
    class_def = content[start_pos:end_pos]
    return start_pos, end_pos

def remove_duplicate_classes(schema_name):
    """
    Elimina clases duplicadas de un archivo generado
    Mantiene solo las clases que pertenecen a ese schema
    """
    file_path = Path(f'app/models/{schema_name}_generated.py')
    
    if not file_path.exists():
        print(f"[SKIP] {file_path} no existe")
        return
    
    print(f"\n[*] Procesando: {file_path}")
    
    # Leer contenido
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Encontrar todas las clases en el archivo
    class_pattern = r'class ([A-Z][a-zA-Z0-9]*)\('
    found_classes = re.findall(class_pattern, content)
    
    print(f"    Clases encontradas: {', '.join(found_classes)}")
    
    # Identificar qué clases deben eliminarse
    classes_to_remove = []
    classes_to_keep = []
    
    for class_name in found_classes:
        owner = get_owner_schema(class_name)
        if owner and owner != schema_name:
            classes_to_remove.append(class_name)
        else:
            classes_to_keep.append(class_name)
    
    if not classes_to_remove:
        print(f"    [OK] No hay duplicados que eliminar")
        return
    
    print(f"    [REMOVE] {', '.join(classes_to_remove)}")
    print(f"    [KEEP] {', '.join(classes_to_keep)}")
    
    # Eliminar clases duplicadas
    new_content = content
    for class_name in classes_to_remove:
        start, end = extract_class_definition(new_content, class_name)
        if start is not None:
            # Eliminar la clase completa
            new_content = new_content[:start] + new_content[end:]
            print(f"    [OK] Eliminado: {class_name}")
    
    # Escribir contenido limpio
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"    [OK] Archivo actualizado")

def add_cross_schema_imports():
    """
    Agrega imports cross-schema donde sea necesario
    """
    # Mapeo de qué schemas necesitan importar de otros
    imports_needed = {
        'operations': {
            'finance': ['Accounts'],
            'product': ['Products', 'ProductVariants']
        },
        'product': {
            'finance': ['Accounts'],
            'operations': ['Orders']
        }
    }
    
    for schema, needed_imports in imports_needed.items():
        file_path = Path(f'app/models/{schema}_generated.py')
        
        if not file_path.exists():
            continue
        
        print(f"\n[*] Agregando imports a: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Buscar dónde insertar los imports (después de los imports de sqlalchemy.orm)
        insert_pattern = r'(from sqlalchemy\.orm import[^\n]+\n)'
        
        # Construir los imports necesarios
        import_lines = '\n# Cross-schema imports\n'
        for from_schema, models in needed_imports.items():
            models_str = ', '.join(models)
            import_lines += f'from app.models.{from_schema}_generated import {models_str}\n'
        
        # Verificar si ya existen los imports
        if 'Cross-schema imports' in content:
            print(f"    [SKIP] Imports ya existen")
            continue
        
        # Insertar imports
        new_content = re.sub(
            insert_pattern,
            r'\1' + import_lines,
            content,
            count=1
        )
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"    [OK] Imports agregados")

if __name__ == "__main__":
    print("="  * 70)
    print("LIMPIEZA DE MODELOS DUPLICADOS")
    print("=" * 70)
    
    # Paso 1: Eliminar duplicados
    print("\n[PASO 1] Eliminando clases duplicadas...")
    for schema in ['operations', 'product', 'finance', 'marketing']:
        remove_duplicate_classes(schema)
    
    # Paso 2: Agregar imports cross-schema
    print("\n[PASO 2] Agregando imports cross-schema...")
    add_cross_schema_imports()
    
    print("\n" + "=" * 70)
    print("[OK] Proceso completado!")
    print("=" * 70)
