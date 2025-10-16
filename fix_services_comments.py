"""
Script final para comentar todas las líneas descriptivas en los servicios
"""
import re

def fix_comments(file_path):
    """
    Fix all uncommented descriptive lines
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    fixed_lines = []
    for line in lines:
        # Fix lines that start with whitespace + "PASO X:" or "REEMPLAZA:" (not commented)
        if re.match(r'^(\s+)(PASO \d+:|REEMPLAZA:)', line):
            # Add # before the text
            match = re.match(r'^(\s+)(.*)', line)
            indentation = match.group(1)
            text = match.group(2)
            fixed_lines.append(f'{indentation}# {text}\n')
        # Fix lines with just === (not commented)
        elif re.match(r'^(\s+)(={10,})\s*$', line):
            match = re.match(r'^(\s+)(.*)', line)
            indentation = match.group(1)
            text = match.group(2)
            fixed_lines.append(f'{indentation}# {text}\n')
        else:
            fixed_lines.append(line)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)

    print(f'OK - {file_path} fixed')

# Fix all three services
print('=' * 80)
print('FIXING COMMENT MARKERS...')
print('=' * 80)

try:
    fix_comments('app/services/purchase_service.py')
    fix_comments('app/services/finance_service.py')
    fix_comments('app/services/marketing_service.py')

    print('=' * 80)
    print('ALL SERVICES FIXED')
    print('=' * 80)

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
