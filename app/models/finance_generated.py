from typing import Optional
import datetime
import decimal

from sqlalchemy import Boolean, CheckConstraint, Computed, DateTime, Enum, ForeignKeyConstraint, Index, Numeric, PrimaryKeyConstraint, String, Text, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.core.database import Base

class Accounts(Base):
    __tablename__ = 'accounts'
    __table_args__ = (
        CheckConstraint('current_balance >= 0::numeric', name='check_balance_not_negative'),
        PrimaryKeyConstraint('account_id', name='accounts_pkey'),
        UniqueConstraint('account_name', name='unique_account_name'),
        Index('idx_accounts_currency_active', 'currency', 'is_active'),
        Index('idx_accounts_type_active', 'account_type', 'is_active'),
        {'comment': 'Cuenta ACC-WALLBIT preconfigurada para pagos de Facebook Ads en '
                'USDT.',
     'schema': 'finance'}
    )

    account_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    account_name: Mapped[str] = mapped_column(String(100), nullable=False, comment='Nombre específico (ej: BNB, Wallbit, Caja Central)')
    account_type: Mapped[str] = mapped_column(Enum('bank', 'crypto_exchange', 'cash', 'payment_gateway', name='account_type', schema='finance'), nullable=False, comment='Tipo de cuenta (bank/crypto_exchange/cash)')
    currency: Mapped[str] = mapped_column(Enum('BOB', 'USD', 'USDT', 'USDC', 'EUR', 'CNY', 'PEN', 'ARS', 'COP', 'PYG', 'BRL', name='currency_code', schema='finance'), nullable=False)
    current_balance: Mapped[decimal.Decimal] = mapped_column(Numeric(15, 2), nullable=False, server_default=text('0'))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('true'))

    financial_transactions: Mapped[list['FinancialTransactions']] = relationship('FinancialTransactions', foreign_keys='[FinancialTransactions.cuenta_destino_id]', back_populates='cuenta_destino')
    financial_transactions_: Mapped[list['FinancialTransactions']] = relationship('FinancialTransactions', foreign_keys='[FinancialTransactions.cuenta_origen_id]', back_populates='cuenta_origen')
    currency_lots: Mapped[list['CurrencyLots']] = relationship('CurrencyLots', back_populates='account')


class FinancialTransactions(Base):
    __tablename__ = 'financial_transactions'
    __table_args__ = (
        CheckConstraint("categoria = 'transferencia_entre_cuentas'::finance.categoria_transaccion AND cuenta_origen_id IS NOT NULL AND cuenta_destino_id IS NOT NULL OR (categoria = ANY (ARRAY['ingreso_por_venta'::finance.categoria_transaccion, 'compra_moneda_extranjera'::finance.categoria_transaccion])) AND cuenta_destino_id IS NOT NULL OR (categoria = ANY (ARRAY['pago_a_proveedor'::finance.categoria_transaccion, 'pago_publicidad_digital'::finance.categoria_transaccion, 'gasto_operativo'::finance.categoria_transaccion])) AND cuenta_origen_id IS NOT NULL OR categoria = 'ajuste_contable'::finance.categoria_transaccion", name='check_cuentas_segun_categoria'),
        CheckConstraint('comision_monto IS NULL OR comision_monto >= 0::numeric', name='check_comision_positiva'),
        CheckConstraint('comision_monto IS NULL OR comision_monto >= 0::numeric', name='check_fee_amount_positive'),
        CheckConstraint('cuenta_origen_id::text IS DISTINCT FROM cuenta_destino_id::text', name='check_different_accounts'),
        CheckConstraint('cuenta_origen_id::text IS DISTINCT FROM cuenta_destino_id::text', name='check_cuentas_diferentes'),
        CheckConstraint("moneda = 'BOB'::finance.currency_code OR tasa_cambio_a_bolivianos IS NOT NULL", name='check_tasa_cambio_requerida'),
        CheckConstraint('monto > 0::numeric', name='check_monto_positivo'),
        CheckConstraint('monto > 0::numeric', name='check_amount_positive'),
        ForeignKeyConstraint(['cuenta_destino_id'], ['finance.accounts.account_id'], ondelete='RESTRICT', name='financial_transactions_to_account_id_fkey'),
        ForeignKeyConstraint(['cuenta_origen_id'], ['finance.accounts.account_id'], ondelete='RESTRICT', name='financial_transactions_from_account_id_fkey'),
        PrimaryKeyConstraint('movimiento_id', name='financial_transactions_pkey'),
        Index('idx_movimientos_categoria', 'categoria'),
        Index('idx_movimientos_cuenta_destino', 'cuenta_destino_id'),
        Index('idx_movimientos_cuenta_origen', 'cuenta_origen_id'),
        Index('idx_movimientos_fecha', 'fecha_transaccion'),
        Index('idx_movimientos_referencia', 'tipo_referencia', 'referencia_id'),
        {'comment': 'Registro central de todas las transacciones financieras. Soporta '
                'ingresos, gastos y\n'
                'transferencias con tracking FIFO para gastos en moneda '
                'extranjera.',
     'schema': 'finance'}
    )

    movimiento_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    monto: Mapped[decimal.Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(Enum('BOB', 'USD', 'USDT', 'USDC', 'EUR', 'CNY', 'PEN', 'ARS', 'COP', 'PYG', 'BRL', name='currency_code', schema='finance'), nullable=False)
    fecha_transaccion: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    categoria: Mapped[str] = mapped_column(Enum('compra_moneda_extranjera', 'pago_a_proveedor', 'pago_publicidad_digital', 'ingreso_por_venta', 'transferencia_entre_cuentas', 'gasto_operativo', 'ajuste_contable', name='categoria_transaccion', schema='finance'), nullable=False)
    cuenta_origen_id: Mapped[Optional[str]] = mapped_column(String(20))
    cuenta_destino_id: Mapped[Optional[str]] = mapped_column(String(20))
    tasa_cambio_a_bolivianos: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(10, 4))
    comision_monto: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(10, 2))
    comision_moneda: Mapped[Optional[str]] = mapped_column(Enum('BOB', 'USD', 'USDT', 'USDC', 'EUR', 'CNY', 'PEN', 'ARS', 'COP', 'PYG', 'BRL', name='currency_code', schema='finance'))
    tipo_referencia: Mapped[Optional[str]] = mapped_column(Enum('purchase', 'payment', 'order', name='tipo_referencia_transaccion', schema='finance'))
    referencia_id: Mapped[Optional[str]] = mapped_column(String(50))
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    notas: Mapped[Optional[str]] = mapped_column(Text)
    costo_total_bolivianos: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(15, 2), Computed("\nCASE\n    WHEN (moneda = 'BOB'::finance.currency_code) THEN monto\n    ELSE (monto * COALESCE(tasa_cambio_a_bolivianos, (0)::numeric))\nEND", persisted=True))

    cuenta_destino: Mapped[Optional['Accounts']] = relationship('Accounts', foreign_keys=[cuenta_destino_id], back_populates='financial_transactions')
    cuenta_origen: Mapped[Optional['Accounts']] = relationship('Accounts', foreign_keys=[cuenta_origen_id], back_populates='financial_transactions_')
    currency_lots: Mapped[list['CurrencyLots']] = relationship('CurrencyLots', back_populates='transaction')
    transaction_lot_consumption: Mapped[list['TransactionLotConsumption']] = relationship('TransactionLotConsumption', back_populates='transaction')


class CurrencyLots(Base):
    __tablename__ = 'currency_lots'
    __table_args__ = (
        CheckConstraint("currency <> 'BOB'::finance.currency_code", name='check_foreign_currency'),
        CheckConstraint('exchange_rate_bob > 0::numeric', name='check_rate_positive'),
        CheckConstraint('original_amount > 0::numeric', name='check_original_positive'),
        CheckConstraint('remaining_amount >= 0::numeric AND remaining_amount <= original_amount', name='check_lot_amounts'),
        ForeignKeyConstraint(['account_id'], ['finance.accounts.account_id'], ondelete='RESTRICT', name='currency_lots_account_id_fkey'),
        ForeignKeyConstraint(['transaction_id'], ['finance.financial_transactions.movimiento_id'], ondelete='RESTRICT', name='currency_lots_transaction_id_fkey'),
        PrimaryKeyConstraint('lot_id', name='currency_lots_pkey'),
        Index('idx_lots_account_currency', 'account_id', 'currency', 'remaining_amount'),
        Index('idx_lots_fifo', 'account_id', 'currency', 'purchase_date', 'lot_id'),
        {'comment': 'Lotes de moneda extranjera para contabilidad FIFO. Cada compra de '
                'moneda extranjera\n'
                'crea un lote que se consume (FIFO) cuando se realizan gastos en '
                'esa moneda.',
     'schema': 'finance'}
    )

    lot_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(20), nullable=False)
    currency: Mapped[str] = mapped_column(Enum('BOB', 'USD', 'USDT', 'USDC', 'EUR', 'CNY', 'PEN', 'ARS', 'COP', 'PYG', 'BRL', name='currency_code', schema='finance'), nullable=False)
    original_amount: Mapped[decimal.Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    remaining_amount: Mapped[decimal.Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    exchange_rate_bob: Mapped[decimal.Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    purchase_date: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

    account: Mapped['Accounts'] = relationship('Accounts', back_populates='currency_lots')
    transaction: Mapped['FinancialTransactions'] = relationship('FinancialTransactions', back_populates='currency_lots')
    transaction_lot_consumption: Mapped[list['TransactionLotConsumption']] = relationship('TransactionLotConsumption', back_populates='lot')


class TransactionLotConsumption(Base):
    __tablename__ = 'transaction_lot_consumption'
    __table_args__ = (
        CheckConstraint('amount_consumed > 0::numeric', name='check_consumed_positive'),
        CheckConstraint('cost_bob > 0::numeric', name='check_cost_positive'),
        ForeignKeyConstraint(['lot_id'], ['finance.currency_lots.lot_id'], ondelete='RESTRICT', name='transaction_lot_consumption_lot_id_fkey'),
        ForeignKeyConstraint(['transaction_id'], ['finance.financial_transactions.movimiento_id'], ondelete='CASCADE', name='transaction_lot_consumption_transaction_id_fkey'),
        PrimaryKeyConstraint('consumption_id', name='transaction_lot_consumption_pkey'),
        Index('idx_consumption_lot', 'lot_id'),
        Index('idx_consumption_transaction', 'transaction_id'),
        {'comment': 'Detalle de consumo de lotes FIFO por transacción. Una transacción '
                'puede consumir\n'
                'múltiples lotes si el monto excede el saldo de un solo lote.',
     'schema': 'finance'}
    )

    consumption_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String(20), nullable=False)
    lot_id: Mapped[str] = mapped_column(String(20), nullable=False)
    amount_consumed: Mapped[decimal.Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    cost_bob: Mapped[decimal.Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    consumed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

    lot: Mapped['CurrencyLots'] = relationship('CurrencyLots', back_populates='transaction_lot_consumption')
    transaction: Mapped['FinancialTransactions'] = relationship('FinancialTransactions', back_populates='transaction_lot_consumption')
