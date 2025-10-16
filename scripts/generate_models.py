#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para generar modelos SQLAlchemy desde la BD existente
Usa subprocess para manejar encoding correctamente en Windows
Post-procesa los archivos para usar Base centralizada
"""
import subprocess
import sys
import re
from pathlib import Path

# Configuracion
DATABASE_URL = "postgresql://postgres:12345@localhost:5432/ecommerce_bo"
SCHEMAS = ["operations", "product", "finance", "marketing"]  # Todos los schemas

def post_process_generated_file(file_path):
    """
    Post-procesa el archivo generado para usar la Base centralizada

    Cambios:
    1. Elimina la definición de clase Base que genera sqlacodegen
    2. Agrega import desde app.core.database
    3. Mantiene todo lo demás intacto
    """
    print(f"[*] Post-procesando: {file_path}")

    try:
        # Leer contenido
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Patron para encontrar y eliminar la definición de Base
        # sqlacodegen genera algo como:
        # class Base(DeclarativeBase):
        #     pass
        base_pattern = r'class Base\(DeclarativeBase\):\s+pass\s*\n'

        # Eliminar la definición de Base
        content = re.sub(base_pattern, '', content)

        # Agregar import de Base después de los imports de SQLAlchemy
        # Buscar la última línea de imports de sqlalchemy.orm
        import_pattern = r'(from sqlalchemy\.orm import[^\n]+\n)'

        # Agregar nuestro import después de los imports de sqlalchemy
        base_import = '\nfrom app.core.database import Base\n'

        if 'from app.core.database import Base' not in content:
            # Insertar después del último import de sqlalchemy.orm
            content = re.sub(
                import_pattern,
                r'\1' + base_import,
                content,
                count=1
            )

        # Escribir contenido modificado
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"[OK] Post-procesamiento completado")
        return True

    except Exception as e:
        print(f"[ERROR] Error en post-procesamiento: {e}")
        return False

def generate_models_for_schema(schema_name):
    """Genera modelos para un schema especifico usando sqlacodegen via subprocess"""
    print(f"\n[*] Generando modelos para schema: {schema_name}")

    output_file = Path(f"app/models/{schema_name}_generated.py")

    # Comando sqlacodegen
    cmd = [
        sys.executable,
        "-m", "sqlacodegen",
        DATABASE_URL,
        "--schemas", schema_name,
        "--nojoined",
        "--outfile", str(output_file)
    ]

    try:
        # Ejecutar con encoding UTF-8 explicito
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',  # Reemplazar caracteres problematicos
            timeout=30
        )

        if result.returncode == 0:
            print(f"[OK] Modelos generados: {output_file}")

            # Verificar que el archivo se creo y tiene contenido
            if output_file.exists():
                size = output_file.stat().st_size
                print(f"     Tamanio: {size} bytes")

                # Post-procesar el archivo para usar Base centralizada
                post_process_generated_file(output_file)
            else:
                print(f"[WARN] Archivo no encontrado: {output_file}")
        else:
            print(f"[ERROR] Error generando modelos para {schema_name}")
            if result.stderr:
                print(f"        Error: {result.stderr}")

    except subprocess.TimeoutExpired:
        print(f"[ERROR] Timeout generando modelos para {schema_name}")
    except Exception as e:
        print(f"[ERROR] Error: {e}")

if __name__ == "__main__":
    print("[*] Generador de Modelos SQLAlchemy v2.0")
    print("=" * 60)
    print("[*] Schemas a generar: operations, product, finance, marketing")
    print("[*] Post-procesamiento: Base centralizada desde app.core.database")
    print("=" * 60)

    # Verificar que sqlacodegen esta instalado
    try:
        result = subprocess.run(
            [sys.executable, "-m", "sqlacodegen", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        print(f"[OK] sqlacodegen version: {result.stdout.strip()}")
    except Exception as e:
        print(f"[ERROR] sqlacodegen no esta instalado: {e}")
        print("        Instalar con: pip install sqlacodegen")
        sys.exit(1)

    # Generar modelos para cada schema
    success_count = 0
    for schema in SCHEMAS:
        try:
            generate_models_for_schema(schema)
            success_count += 1
        except Exception as e:
            print(f"[ERROR] Error en schema {schema}: {e}")

    print("\n" + "=" * 60)
    print(f"[OK] Proceso completado! ({success_count}/{len(SCHEMAS)} schemas generados)")
    print("=" * 60)
