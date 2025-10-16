"""
Script para descomentar y activar el código de los servicios
"""
import re

def uncomment_service_code(file_path):
    """Descomentar código en un archivo de servicio"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Contar bloques comentados antes
    commented_blocks_before = content.count('# Nota: Descomentar')

    # Patrones de reemplazo
    replacements = [
        # Patrón 1: Bloque completo comentado con # al inicio de cada línea
        (r'# Nota: Descomentar.*?\n((?:        # .*\n)*)', ''),  # Eliminar la nota
        (r'^(        # )', '        ', re.MULTILINE),  # Descomentar líneas con indentación de 8 espacios
        (r'^(            # )', '            ', re.MULTILINE),  # 12 espacios
        (r'^(                # )', '                ', re.MULTILINE),  # 16 espacios
        (r'^(    # )', '    ', re.MULTILINE),  # 4 espacios
        (r'^(        #     )', '            ', re.MULTILINE),  # Espacios + comentario
    ]

    # Eliminar todas las líneas que dicen "# Nota: Descomentar"
    content = re.sub(r'.*# Nota: Descomentar.*\n', '', content)

    # Eliminar comentarios # al inicio de líneas indentadas (código comentado)
    lines = content.split('\n')
    new_lines = []

    for line in lines:
        # Si la línea tiene indentación seguida de "# " (código comentado)
        if re.match(r'^(\s+)# ([^\s].*)', line):
            # Eliminar el "# " pero mantener la indentación
            new_line = re.sub(r'^(\s+)# ', r'\1', line)
            new_lines.append(new_line)
        else:
            new_lines.append(line)

    content = '\n'.join(new_lines)

    # Eliminar bloques de código que eran placeholders
    # Buscar y eliminar líneas como: logger.info(f"ℹ️ ... - Placeholder")
    # Buscar y eliminar líneas como: return (0, Decimal('0'))
    content = re.sub(r'.*logger\.info\(f".*Placeholder.*\n', '', content)
    content = re.sub(r'.*# Placeholder.*\n', '', content)

    # Escribir archivo actualizado
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f'OK - {file_path} actualizado')
    print(f'  Bloques descomentados (aprox)')

# Activar servicios
print('=' * 80)
print('DESCOMENTANDO Y ACTIVANDO SERVICIOS...')
print('=' * 80)

uncomment_service_code('D:/Projects/ecommerce_bo/backend/app/services/purchase_service.py')
uncomment_service_code('D:/Projects/ecommerce_bo/backend/app/services/finance_service.py')
uncomment_service_code('D:/Projects/ecommerce_bo/backend/app/services/marketing_service.py')

print('=' * 80)
print('TODOS LOS SERVICIOS ACTIVADOS')
print('=' * 80)
