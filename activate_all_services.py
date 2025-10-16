"""
Script para activar todos los servicios descomentando código
"""
import re

def activate_service(file_path):
    """Activa un servicio descomentando todo su código"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Eliminar líneas de "Nota: Descomentar"
    content = re.sub(r'.*# Nota: Descomentar.*\n', '', content)

    # 2. Descomentar imports de modelos
    content = content.replace(
        '# from app.models import Purchases, PurchaseItems, Suppliers',
        'from app.models import Purchases, PurchaseItems, Suppliers\nfrom sqlalchemy import func'
    )
    content = content.replace(
        '# from app.models import Accounts, FinancialTransactions, CurrencyLots, TransactionLotConsumption',
        'from app.models import Accounts, FinancialTransactions, CurrencyLots, TransactionLotConsumption\nfrom sqlalchemy import func'
    )
    content = content.replace(
        '# from app.models import Ads, AdDailyMetrics, AdCreativeVersions, Campaigns',
        'from app.models import Ads, AdDailyMetrics, AdCreativeVersions, Campaigns\nfrom sqlalchemy import func'
    )

    # 3. Descomentar líneas individuales (# con espacios antes)
    lines = content.split('\n')
    new_lines = []
    for i, line in enumerate(lines):
        # Si es una línea comentada con indentación
        if re.match(r'^(\s+)# ([^#\s])', line):
            # Descomentar
            new_line = re.sub(r'^(\s+)# ', r'\1', line)
            new_lines.append(new_line)
        else:
            new_lines.append(line)

    content = '\n'.join(new_lines)

    # 4. Eliminar placeholders y mocks
    # Buscar y eliminar bloques de Placeholder
    content = re.sub(r'        # Placeholder mientras se crean los modelos\n.*?return MockSupplier\(\)', '', content, flags=re.DOTALL)
    content = re.sub(r'.*logger\.info\(f"ℹ️.*Placeholder.*\n', '', content)
    content = re.sub(r'        logger\.info\(f"ℹ️.*Placeholder.*\n.*return.*\n', '', content)

    # 5. Quitar "# Nota: Descomentar cuando exista FinanceService"
    content = re.sub(r'.*# Nota: Descomentar cuando exista FinanceService.*\n', '', content)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f'OK - {file_path} - ACTIVADO')

# Activar los 3 servicios
print('=' * 80)
print('ACTIVANDO TODOS LOS SERVICIOS...')
print('=' * 80)

try:
    activate_service('app/services/purchase_service.py')
    activate_service('app/services/finance_service.py')
    activate_service('app/services/marketing_service.py')

    print('=' * 80)
    print('TODOS LOS SERVICIOS ACTIVADOS EXITOSAMENTE')
    print('=' * 80)

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
