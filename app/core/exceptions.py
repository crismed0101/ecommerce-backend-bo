"""
Excepciones personalizadas del sistema

Principio: Fail Fast - Lanzar excepciones claras y específicas
"""


class BaseAppException(Exception):
    """Base para todas las excepciones de la app"""

    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


# ==================== PRODUCT ====================

class ProductNotFoundException(BaseAppException):
    """Producto no encontrado"""
    pass


class InsufficientStockException(BaseAppException):
    """Stock insuficiente para completar operación"""

    def __init__(self, product_variant_id: str, requested: int, available: int):
        super().__init__(
            message=f"Stock insuficiente para {product_variant_id}",
            details={
                "product_variant_id": product_variant_id,
                "requested": requested,
                "available": available
            }
        )


# ==================== OPERATIONS ====================

class OrderNotFoundException(BaseAppException):
    """Orden no encontrada"""

    def __init__(self, order_id: str):
        super().__init__(
            message=f"Orden {order_id} no encontrada",
            details={"order_id": order_id}
        )


class InvalidOrderStatusException(BaseAppException):
    """Estado de orden inválido"""

    def __init__(self, current_status: str, new_status: str):
        super().__init__(
            message=f"No se puede cambiar de {current_status} a {new_status}",
            details={"current_status": current_status, "new_status": new_status}
        )


class CustomerNotFoundException(BaseAppException):
    """Cliente no encontrado"""
    pass


# ==================== FINANCE ====================

class InsufficientBalanceException(BaseAppException):
    """Saldo insuficiente en cuenta"""

    def __init__(self, account_id: str, balance: float, required: float):
        super().__init__(
            message=f"Saldo insuficiente en cuenta {account_id}",
            details={
                "account_id": account_id,
                "balance": balance,
                "required": required
            }
        )


class AccountNotFoundException(BaseAppException):
    """Cuenta no encontrada"""
    pass
