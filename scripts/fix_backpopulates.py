#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para eliminar back_populates problemáticos en relaciones cross-schema
"""
import re
from pathlib import Path

def fix_backpopulates(file_path, fixes):
    """
    Elimina back_populates específicos de un archivo
    
    fixes: lista de tuplas (relationship_name, back_populates_to_remove)
    """
    print(f"\n[*] Procesando: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    modified = False
    for rel_name, back_pop in fixes:
        # Buscar el relationship y eliminar back_populates
        pattern = rf"({rel_name}:[^\n]+relationship\([^)]+), back_populates='{back_pop}'"
        
        if re.search(pattern, content):
            content = re.sub(pattern, r'\1', content)
            print(f"    [OK] Eliminado back_populates='{back_pop}' de {rel_name}")
            modified = True
    
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"    [OK] Archivo actualizado")
    else:
        print(f"    [SKIP] No se encontraron back_populates problemáticos")

if __name__ == "__main__":
    print("="  * 70)
    print("ELIMINACIÓN DE BACK_POPULATES PROBLEMÁTICOS")
    print("=" * 70)
    
    # Definir qué back_populates eliminar de cada archivo
    fixes = {
        'app/models/operations_generated.py': [
            ('received_in_wallet', 'payments'),
        ],
        'app/models/product_generated.py': [
            ('payment_account', 'purchases'),
        ]
    }
    
    for file_path, file_fixes in fixes.items():
        path = Path(file_path)
        if path.exists():
            fix_backpopulates(path, file_fixes)
    
    print("\n" + "=" * 70)
    print("[OK] Proceso completado!")
    print("=" * 70)
