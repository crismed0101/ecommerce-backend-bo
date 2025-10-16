"""
FinanceService - Gestión financiera multi-moneda con sistema FIFO

REEMPLAZA TRIGGERS:
- finance.trg_10_update_balances
- finance.trg_01_validate_currencies
- finance.trg_02_validate_sufficient_balance
- finance.trg_11_consume_lots_fifo
- finance.trg_12_create_currency_lot
- finance.trg_recalcular_lote_tras_consumo
- finance.trg_lots_validate_consistency
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional, Tuple, List
from decimal import Decimal
from datetime import datetime
import logging

from app.models import Accounts, FinancialTransactions, CurrencyLots, TransactionLotConsumption
from app.services.id_generator import IDGenerator

logger = logging.getLogger(__name__)


class FinanceService:
    """Service para gestión financiera multi-moneda con FIFO"""

    @staticmethod
    def create_transaction(
        db: Session,
        transaction_type: str,
        from_account_id: Optional[str],
        to_account_id: Optional[str],
        amount: Decimal,
        currency: str,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        description: Optional[str] = None,
        transaction_date: Optional[datetime] = None
    ):
        """
        Crear transacción financiera completa con validaciones, actualización de balances y FIFO

        Args:
            transaction_type: 'income', 'expense', 'transfer'
            amount: Siempre positivo
        """
        try:
            if transaction_date is None:
                transaction_date = datetime.now()

            FinanceService._validate_currencies(db, from_account_id, to_account_id)

            if transaction_type in ['expense', 'transfer']:
                FinanceService._validate_sufficient_balance(db, from_account_id, amount, currency)

            transaction_id = IDGenerator.generate_transaction_id(db)
            transaction = FinancialTransactions(
                transaction_id=transaction_id,
                transaction_type=transaction_type,
                from_account_id=from_account_id,
                to_account_id=to_account_id,
                amount=amount,
                currency=currency,
                reference_type=reference_type,
                reference_id=reference_id,
                description=description,
                transaction_date=transaction_date
            )
            db.add(transaction)
            db.flush()

            logger.info(f"Transacción creada: {transaction_id} ({transaction_type}, {amount} {currency})")

            FinanceService._update_balances(
                db=db,
                transaction_type=transaction_type,
                from_account_id=from_account_id,
                to_account_id=to_account_id,
                amount=amount,
                currency=currency
            )

            if transaction_type in ['expense', 'transfer'] and from_account_id:
                FinanceService._consume_lots_fifo(
                    db=db,
                    account_id=from_account_id,
                    amount=amount,
                    currency=currency,
                    transaction_id=transaction_id
                )

            if transaction_type in ['income', 'transfer'] and to_account_id:
                FinanceService._create_currency_lot(
                    db=db,
                    account_id=to_account_id,
                    amount=amount,
                    currency=currency,
                    transaction_id=transaction_id,
                    lot_date=transaction_date
                )

            db.commit()
            return transaction

        except Exception as e:
            db.rollback()
            logger.error(f"Error creando transacción: {str(e)}")
            raise ValueError(f"Error creando transacción: {str(e)}")

    @staticmethod
    def _validate_currencies(db: Session, from_account_id: Optional[str], to_account_id: Optional[str]):
        """Validar que from_account y to_account tengan la misma moneda"""
        if not from_account_id or not to_account_id:
            return

        from_account = db.query(Accounts).filter(Accounts.account_id == from_account_id).first()
        to_account = db.query(Accounts).filter(Accounts.account_id == to_account_id).first()

        if not from_account:
            raise ValueError(f"Cuenta origen {from_account_id} no encontrada")
        if not to_account:
            raise ValueError(f"Cuenta destino {to_account_id} no encontrada")
        if from_account.currency != to_account.currency:
            raise ValueError(f"Monedas no coinciden: {from_account.currency} != {to_account.currency}")

        logger.debug(f"Monedas validadas: {from_account_id} <-> {to_account_id}")

    @staticmethod
    def _validate_sufficient_balance(db: Session, account_id: str, amount: Decimal, currency: str):
        """Validar que la cuenta tenga saldo suficiente"""
        account = db.query(Accounts).filter(Accounts.account_id == account_id).first()
        if not account:
            raise ValueError(f"Cuenta {account_id} no encontrada")
        if account.balance < amount:
            raise ValueError(f"Saldo insuficiente en cuenta {account_id}: {account.balance} {currency} < {amount} {currency}")

        logger.debug(f"Saldo validado: cuenta {account_id} tiene fondos suficientes")

    @staticmethod
    def _update_balances(
        db: Session,
        transaction_type: str,
        from_account_id: Optional[str],
        to_account_id: Optional[str],
        amount: Decimal,
        currency: str
    ):
        """Actualizar balances de cuentas tras transacción"""
        if from_account_id:
            from_account = db.query(Accounts).filter(Accounts.account_id == from_account_id).first()
            if from_account:
                from_account.balance -= amount
                logger.info(f"Cuenta {from_account_id}: -{amount} {currency} (nuevo balance: {from_account.balance})")

        if to_account_id:
            to_account = db.query(Accounts).filter(Accounts.account_id == to_account_id).first()
            if to_account:
                to_account.balance += amount
                logger.info(f"Cuenta {to_account_id}: +{amount} {currency} (nuevo balance: {to_account.balance})")

        db.flush()
        logger.info(f"Balances actualizados para transacción {transaction_type}")

    @staticmethod
    def _create_currency_lot(
        db: Session,
        account_id: str,
        amount: Decimal,
        currency: str,
        transaction_id: str,
        lot_date: datetime
    ):
        """Crear lote de moneda al recibir fondos (sistema FIFO)"""
        lot_id = IDGenerator.generate_lot_id(db)
        lot = CurrencyLots(
            lot_id=lot_id,
            account_id=account_id,
            amount=amount,
            remaining_amount=amount,
            currency=currency,
            transaction_id=transaction_id,
            lot_date=lot_date
        )
        db.add(lot)
        db.flush()
        logger.info(f"Lote creado: {amount} {currency} para cuenta {account_id}")

    @staticmethod
    def _consume_lots_fifo(db: Session, account_id: str, amount: Decimal, currency: str, transaction_id: str):
        """Consumir lotes de moneda en orden FIFO (First In First Out)"""
        lots = db.query(CurrencyLots).filter(
            CurrencyLots.account_id == account_id,
            CurrencyLots.currency == currency,
            CurrencyLots.remaining_amount > 0
        ).order_by(
            CurrencyLots.lot_date.asc()
        ).all()

        remaining_to_consume = amount

        for lot in lots:
            if remaining_to_consume <= 0:
                break

            consumed_from_lot = min(lot.remaining_amount, remaining_to_consume)

            consumption_id = IDGenerator.generate_consumption_id(db)
            consumption = TransactionLotConsumption(
                consumption_id=consumption_id,
                lot_id=lot.lot_id,
                transaction_id=transaction_id,
                consumed_amount=consumed_from_lot,
                consumption_date=datetime.now()
            )
            db.add(consumption)

            lot.remaining_amount -= consumed_from_lot
            remaining_to_consume -= consumed_from_lot

            logger.info(f"Lote {lot.lot_id}: -{consumed_from_lot} {currency} (restante: {lot.remaining_amount})")

        if remaining_to_consume > 0:
            raise ValueError(f"Lotes insuficientes: faltan {remaining_to_consume} {currency}")

        db.flush()
        logger.info(f"Consumo FIFO: {amount} {currency} de cuenta {account_id}")

    @staticmethod
    def _recalculate_lot(db: Session, lot_id: str) -> Decimal:
        """Recalcular cantidad restante en lote desde consumos (IDEMPOTENTE)"""
        lot = db.query(CurrencyLots).filter(CurrencyLots.lot_id == lot_id).first()
        if not lot:
            raise ValueError(f"Lote {lot_id} no encontrado")

        total_consumed = db.query(
            func.coalesce(func.sum(TransactionLotConsumption.consumed_amount), 0)
        ).filter(
            TransactionLotConsumption.lot_id == lot_id
        ).scalar()

        new_remaining = lot.amount - Decimal(str(total_consumed))
        lot.remaining_amount = new_remaining
        db.flush()

        logger.info(f"Lote {lot_id} recalculado: {new_remaining} restante")
        return new_remaining

    @staticmethod
    def _validate_lot_consistency(db: Session, lot_id: str):
        """Validar consistencia de lote"""
        lot = db.query(CurrencyLots).filter(CurrencyLots.lot_id == lot_id).first()
        if not lot:
            raise ValueError(f"Lote {lot_id} no encontrado")

        if lot.remaining_amount < 0:
            raise ValueError(f"Lote {lot_id} tiene remaining_amount negativo: {lot.remaining_amount}")

        total_consumed = db.query(
            func.coalesce(func.sum(TransactionLotConsumption.consumed_amount), 0)
        ).filter(
            TransactionLotConsumption.lot_id == lot_id
        ).scalar()

        expected_remaining = lot.amount - Decimal(str(total_consumed))
        if lot.remaining_amount != expected_remaining:
            raise ValueError(f"Lote {lot_id} inconsistente: remaining={lot.remaining_amount}, expected={expected_remaining}")

        logger.debug(f"Lote {lot_id} validado (consistente)")

    @staticmethod
    def get_account_balance(db: Session, account_id: str) -> Tuple[Decimal, str]:
        """Obtener balance actual de cuenta"""
        account = db.query(Accounts).filter(Accounts.account_id == account_id).first()
        if not account:
            raise ValueError(f"Cuenta {account_id} no encontrada")
        return (account.balance, account.currency)

    @staticmethod
    def get_lots_for_account(
        db: Session,
        account_id: str,
        currency: Optional[str] = None,
        only_available: bool = True
    ) -> List:
        """Obtener lotes de una cuenta"""
        query = db.query(CurrencyLots).filter(CurrencyLots.account_id == account_id)

        if currency:
            query = query.filter(CurrencyLots.currency == currency)
        if only_available:
            query = query.filter(CurrencyLots.remaining_amount > 0)

        return query.order_by(CurrencyLots.lot_date.asc()).all()

    @staticmethod
    def get_transaction_history(db: Session, account_id: str, limit: int = 50) -> List:
        """Obtener historial de transacciones de una cuenta"""
        return db.query(FinancialTransactions).filter(
            or_(
                FinancialTransactions.from_account_id == account_id,
                FinancialTransactions.to_account_id == account_id
            )
        ).order_by(
            FinancialTransactions.transaction_date.desc()
        ).limit(limit).all()
