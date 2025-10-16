"""
Final comprehensive fix for all service files
"""
import re

def final_fix(file_path):
    """Fix all remaining issues"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Remove standalone # lines (just whitespace + # + whitespace)
        if re.match(r'^\s+#\s*$', line):
            i += 1
            continue

        # Fix lines with extra leading spaces before proper indentation
        # Example: "             purchase.total" should be "            purchase.total"
        if re.match(r'^(\s+) (.+)', line):
            # Check if has leading space before indentation
            match = re.match(r'^( +)(\s{4,})(.+)', line)
            if match and len(match.group(1)) <= 8:  # Leading space(s) before real indent
                indentation = match.group(2)
                content = match.group(3)
                fixed_lines.append(f'{indentation}{content}\n')
                i += 1
                continue

        fixed_lines.append(line)
        i += 1

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)

    print(f'OK - {file_path}')

# Fix all three services
print('=' * 80)
print('FINAL FIX - ALL SERVICES')
print('=' * 80)

try:
    final_fix('app/services/purchase_service.py')
    final_fix('app/services/finance_service.py')
    final_fix('app/services/marketing_service.py')

    print('=' * 80)
    print('ALL FIXES APPLIED')
    print('=' * 80)

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
