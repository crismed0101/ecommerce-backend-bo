#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para solucionar imports circulares usando TYPE_CHECKING
"""
import re
from pathlib import Path

def fix_circular_imports(file_path):
    """
    Mueve los imports cross-schema a un bloque TYPE_CHECKING
    """
    print(f"\n[*] Procesando: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar el bloque de imports cross-schema
    cross_schema_pattern = r'# Cross-schema imports\n((?:from app\.models\.\w+_generated import [^\n]+\n)+)'
    
    match = re.search(cross_schema_pattern, content)
    
    if not match:
        print(f"    [SKIP] No hay imports cross-schema")
        return
    
    cross_imports = match.group(1)
    
    # Verificar si ya está usando TYPE_CHECKING
    if 'TYPE_CHECKING' in content:
        print(f"    [SKIP] Ya usa TYPE_CHECKING")
        return
    
    # Crear el nuevo bloque con TYPE_CHECKING
    new_block = """# Cross-schema imports (lazy para evitar circular imports)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
""" + "    " + cross_imports.replace("\n", "\n    ").strip() + "\n"
    
    # Reemplazar el bloque antiguo
    new_content = content.replace(
        '# Cross-schema imports\n' + cross_imports,
        new_block
    )
    
    # Escribir el archivo actualizado
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"    [OK] Imports movidos a TYPE_CHECKING")

if __name__ == "__main__":
    print("="  * 70)
    print("SOLUCIÓN DE IMPORTS CIRCULARES")
    print("=" * 70)
    
    files_to_fix = [
        Path('app/models/operations_generated.py'),
        Path('app/models/product_generated.py')
    ]
    
    for file_path in files_to_fix:
        if file_path.exists():
            fix_circular_imports(file_path)
    
    print("\n" + "=" * 70)
    print("[OK] Proceso completado!")
    print("=" * 70)
    print("\nNota: Los imports con TYPE_CHECKING solo se usan para type hints,")
    print("no para uso en runtime. Esto elimina los imports circulares.")
