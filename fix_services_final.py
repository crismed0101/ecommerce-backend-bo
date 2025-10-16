"""
Script para arreglar los archivos de servicios después de la activación
"""
import re

def fix_service_file(file_path):
    """
    Arreglar un archivo de servicio:
    1. Re-comentar líneas decorativas (====)
    2. Re-comentar etiquetas descriptivas (PASO X:, etc.)
    3. Descomentar código real (# seguido de espacios + código)
    4. Eliminar placeholders y líneas vacías redundantes
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Re-comentar líneas con solo ====
    content = re.sub(r'^(\s+)(={10,})$', r'\1# \2', content, flags=re.MULTILINE)

    # 2. Re-comentar etiquetas descriptivas (PASO X:, etc.)
    content = re.sub(r'^(\s+)(PASO \d+:.*?)$', r'\1# \2', content, flags=re.MULTILINE)
    content = re.sub(r'^(\s+)(REEMPLAZA:.*?)$', r'\1# \2', content, flags=re.MULTILINE)

    # 3. Descomentar código real en múltiples pasos
    lines = content.split('\n')
    fixed_lines = []

    for i, line in enumerate(lines):
        # Si es una línea que empieza con espacios + #  + más espacios + código
        # Ejemplo: "#     purchase_id=purchase_id,"
        if re.match(r'^(\s+)#(\s{1,5})([a-zA-Z_].*)', line):
            # Descomentar: quitar el # pero mantener indentación
            match = re.match(r'^(\s+)#(\s{1,5})(.*)', line)
            indentation = match.group(1)
            spaces_after = match.group(2)
            code = match.group(3)
            fixed_line = indentation + spaces_after + code
            fixed_lines.append(fixed_line)
        # Si es una línea que empieza con espacios + # + código directo
        # Ejemplo: "# supplier = db.query..."
        elif re.match(r'^(\s+)# ([a-zA-Z_].*)', line):
            # Descomentar
            match = re.match(r'^(\s+)# (.*)', line)
            indentation = match.group(1)
            code = match.group(2)
            fixed_line = indentation + code
            fixed_lines.append(fixed_line)
        # Si es una línea con doble comentario # # algo
        elif re.match(r'^(\s+)# # (.*)', line):
            # Quitar el primer # y mantener el segundo #
            match = re.match(r'^(\s+)# (# .*)', line)
            indentation = match.group(1)
            comment = match.group(2)
            fixed_line = indentation + comment
            fixed_lines.append(fixed_line)
        else:
            fixed_lines.append(line)

    content = '\n'.join(fixed_lines)

    # 4. Eliminar bloques de placeholder
    content = re.sub(r'\s+Placeholder mientras se crean los modelos.*?return MockSupplier\(\)', '', content, flags=re.DOTALL)
    content = re.sub(r'\s+class MockSupplier:.*?return MockSupplier\(\)', '', content, flags=re.DOTALL)

    # 5. Limpiar return statements duplicados o placeholders
    content = re.sub(r'\n\s+return \(0, Decimal\(\'0\'\)\)\n', '\n', content)
    content = re.sub(r'\n\s+return None\n\s+return None', '\n        return None', content)
    content = re.sub(r'\n\s+return \[\]\n\s+return \[\]', '\n        return []', content)

    # 6. Limpiar líneas en blanco múltiples (más de 2 seguidas)
    content = re.sub(r'\n{4,}', '\n\n\n', content)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f'OK - {file_path} arreglado')

# Arreglar los 3 servicios
print('=' * 80)
print('ARREGLANDO SERVICIOS...')
print('=' * 80)

try:
    fix_service_file('app/services/purchase_service.py')
    fix_service_file('app/services/finance_service.py')
    fix_service_file('app/services/marketing_service.py')

    print('=' * 80)
    print('TODOS LOS SERVICIOS ARREGLADOS')
    print('=' * 80)

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
