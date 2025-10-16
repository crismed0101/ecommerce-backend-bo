from typing import Optional
import datetime
import decimal

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, DateTime, Enum, ForeignKeyConstraint, Index, Integer, JSON, Numeric, PrimaryKeyConstraint, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Cross-schema imports (lazy para evitar circular imports)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.finance_generated import Accounts
    from app.models.product_generated import Products, ProductVariants

from app.core.database import Base


class Carriers(Base):
    __tablename__ = 'carriers'
    __table_args__ = (
        CheckConstraint("jsonb_typeof(contacts) = 'object'::text", name='check_contacts_structure'),
        PrimaryKeyConstraint('carrier_id', name='carriers_pkey'),
        UniqueConstraint('company_name', name='unique_carrier_company_name'),
        Index('idx_carriers_contacts', 'contacts'),
        {'schema': 'operations'}
    )

    carrier_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    company_name: Mapped[str] = mapped_column(String(100), nullable=False)
    contacts: Mapped[Optional[dict]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('true'))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

    carrier_rates: Mapped[list['CarrierRates']] = relationship('CarrierRates', back_populates='carrier')
    orders: Mapped[list['Orders']] = relationship('Orders', back_populates='carrier')
    payments: Mapped[list['Payments']] = relationship('Payments', back_populates='carrier')


class Customers(Base):
    __tablename__ = 'customers'
    __table_args__ = (
        CheckConstraint('total_orders >= 0 AND total_orders_delivered >= 0 AND total_orders_returned >= 0 AND total_orders_cancelled >= 0 AND total_spent_bob >= 0::numeric', name='check_totals_not_negative'),
        PrimaryKeyConstraint('customer_id', name='customers_pkey'),
        UniqueConstraint('phone', name='customers_phone_key'),
        Index('idx_customers_active', 'is_active'),
        Index('idx_customers_department', 'department'),
        Index('idx_customers_email', 'email'),
        Index('idx_customers_ip', 'customer_ip'),
        {'comment': 'Clientes del sistema. customer_id se genera AUTOMÁTICAMENTE via '
                'trigger.\n'
                'Estadísticas se actualizan automáticamente mediante triggers.\n'
                'phone es UNIQUE - no se permiten clientes duplicados con el mismo '
                'teléfono.',
     'schema': 'operations'}
    )

    customer_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False, comment='Nombre completo del cliente (no separado en first/last name)')
    phone: Mapped[str] = mapped_column(String(20), nullable=False, comment='Teléfono del cliente (UNIQUE - no se permiten duplicados)')
    email: Mapped[Optional[str]] = mapped_column(String(150))
    department: Mapped[Optional[str]] = mapped_column(Enum('LA PAZ', 'EL ALTO', 'COCHABAMBA', 'SANTA CRUZ', 'ORURO', 'POTOSI', 'TARIJA', 'SUCRE', 'BENI', 'PANDO', name='department_delivery', schema='operations'), comment='Departamento/Ciudad de Bolivia (son equivalentes)')
    address: Mapped[Optional[str]] = mapped_column(Text, comment='Dirección del cliente')
    reference: Mapped[Optional[str]] = mapped_column(Text, comment='Referencias adicionales para ubicar la dirección')
    google_maps_url: Mapped[Optional[str]] = mapped_column(Text, comment='URL o coordenadas de Google Maps de la ubicación del cliente')
    customer_ip: Mapped[Optional[str]] = mapped_column(String(45), comment='Dirección IP del cliente (IPv4 o IPv6)')
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('true'))
    total_orders: Mapped[Optional[int]] = mapped_column(Integer, server_default=text('0'), comment='Total de órdenes (todos los estados)')
    total_orders_delivered: Mapped[Optional[int]] = mapped_column(Integer, server_default=text('0'), comment='Total de órdenes entregadas exitosamente')
    total_orders_returned: Mapped[Optional[int]] = mapped_column(Integer, server_default=text('0'), comment='Total de órdenes devueltas')
    total_orders_cancelled: Mapped[Optional[int]] = mapped_column(Integer, server_default=text('0'), comment='Total de órdenes canceladas')
    total_spent_bob: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(15, 2), server_default=text('0'), comment='Total gastado en órdenes entregadas (BOB)')

    orders: Mapped[list['Orders']] = relationship('Orders', back_populates='customer')



class CarrierRates(Base):
    __tablename__ = 'carrier_rates'
    __table_args__ = (
        CheckConstraint('commission_delivery >= 0::numeric', name='check_commission_delivery_positive'),
        CheckConstraint('commission_express >= 0::numeric', name='check_commission_express_positive'),
        CheckConstraint('commission_return >= 0::numeric', name='check_commission_return_positive'),
        ForeignKeyConstraint(['carrier_id'], ['operations.carriers.carrier_id'], ondelete='CASCADE', name='fk_rates_carrier'),
        PrimaryKeyConstraint('rate_id', name='carrier_rates_new_pkey'),
        UniqueConstraint('carrier_id', 'department', name='unique_carrier_department'),
        Index('idx_rates_carrier', 'carrier_id'),
        Index('idx_rates_carrier_dept', 'carrier_id', 'department'),
        Index('idx_rates_department', 'department'),
        {'schema': 'operations'}
    )

    rate_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    carrier_id: Mapped[str] = mapped_column(String(20), nullable=False)
    department: Mapped[str] = mapped_column(Enum('LA PAZ', 'COCHABAMBA', 'SANTA CRUZ', 'ORURO', 'POTOSI', 'TARIJA', 'CHUQUISACA', 'BENI', 'PANDO', name='department_stock', schema='product'), nullable=False)
    commission_delivery: Mapped[decimal.Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    commission_return: Mapped[decimal.Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    commission_express: Mapped[decimal.Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

    carrier: Mapped['Carriers'] = relationship('Carriers', back_populates='carrier_rates')


class Orders(Base):
    __tablename__ = 'orders'
    __table_args__ = (
        CheckConstraint('total >= 0::numeric AND priority_shipping_cost >= 0::numeric AND delivery_cost >= 0::numeric AND return_cost >= 0::numeric', name='check_order_amounts'),
        ForeignKeyConstraint(['carrier_id'], ['operations.carriers.carrier_id'], ondelete='RESTRICT', name='orders_carrier_id_fkey'),
        ForeignKeyConstraint(['customer_id'], ['operations.customers.customer_id'], ondelete='RESTRICT', name='orders_customer_id_fkey'),
        PrimaryKeyConstraint('order_id', name='orders_pkey'),
        Index('idx_orders_carrier', 'carrier_id'),
        Index('idx_orders_customer', 'customer_id'),
        Index('idx_orders_external_id', 'external_order_id'),
        Index('idx_orders_utm_content', 'utm_content'),
        Index('idx_orders_utm_source', 'utm_source'),
        {'comment': 'Órdenes de compra. order_id se genera AUTOMÁTICAMENTE via '
                'trigger.\n'
                'El subtotal y total se calculan automáticamente desde '
                'order_items.\n'
                'El estado de la orden se gestiona en order_tracking (1-to-1).\n'
                'La dirección de entrega se obtiene del customer.\n'
                'order_tracking se crea AUTOMÁTICAMENTE al crear la orden.',
     'schema': 'operations'}
    )

    order_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(20), nullable=False)
    total: Mapped[decimal.Decimal] = mapped_column(Numeric(15, 2), nullable=False, server_default=text('0'), comment='Precio total del pedido (viene de Shopify). No se autocalcula. Debe ser >= 0.')
    notes: Mapped[Optional[str]] = mapped_column(Text, comment='Notas adicionales de la orden')
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    is_priority_shipping: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('false'), comment='TRUE si el cliente solicitó envío prioritario.')
    priority_shipping_cost: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(15, 2), server_default=text('0'), comment='Monto que el cliente pagó por envío prioritario (si aplica).')
    carrier_id: Mapped[Optional[str]] = mapped_column(String(20), comment='Transportista asignado. Se llena MANUALMENTE cuando se despacha el pedido.')
    delivery_cost: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(15, 2), server_default=text('0'), comment='Costo/comisión de entrega. Se calcula automáticamente desde carrier_rates cuando order_status = delivered.\nEjemplo: Pedido 100 Bs, delivery_cost 25 Bs → Comerciante recibe 75 Bs.')
    return_cost: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(15, 2), server_default=text('0'), comment='Costo/comisión de devolución. Se calcula automáticamente desde carrier_rates cuando order_status = returned.')
    utm_source: Mapped[Optional[str]] = mapped_column(String(50))
    utm_medium: Mapped[Optional[str]] = mapped_column(String(50))
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(100))
    utm_content: Mapped[Optional[str]] = mapped_column(String(100))
    utm_term: Mapped[Optional[str]] = mapped_column(String(100))
    external_order_id: Mapped[Optional[str]] = mapped_column(String(100))

    carrier: Mapped[Optional['Carriers']] = relationship('Carriers', back_populates='orders')
    customer: Mapped['Customers'] = relationship('Customers', back_populates='orders')
    order_items: Mapped[list['OrderItems']] = relationship('OrderItems', back_populates='order')
    payment_orders: Mapped[list['PaymentOrders']] = relationship('PaymentOrders', back_populates='order')
    tracking: Mapped[Optional['OrderTracking']] = relationship('OrderTracking', back_populates='order', uselist=False)


class Payments(Base):
    __tablename__ = 'payments'
    __table_args__ = (
        CheckConstraint("payment_status = 'paid'::operations.payment_status AND paid_date IS NOT NULL AND received_in_wallet_id IS NOT NULL AND total_final_amount > 0::numeric OR payment_status = 'pending'::operations.payment_status AND paid_date IS NULL AND received_in_wallet_id IS NULL", name='check_paid_date'),
        CheckConstraint('total_deliveries >= 0 AND total_returns >= 0 AND total_deliveries_amount >= 0::numeric AND total_returns_amount >= 0::numeric', name='check_payment_amounts'),
        ForeignKeyConstraint(['carrier_id'], ['operations.carriers.carrier_id'], ondelete='RESTRICT', name='fk_payments_carrier'),
        ForeignKeyConstraint(['received_in_wallet_id'], ['finance.accounts.account_id'], ondelete='RESTRICT', name='payments_received_in_wallet_id_fkey'),
        PrimaryKeyConstraint('payment_id', name='payments_pkey'),
        UniqueConstraint('carrier_id', 'week_start_date', name='unique_carrier_week'),
        Index('idx_payments_carrier', 'carrier_id'),
        Index('idx_payments_status', 'payment_status'),
        Index('idx_payments_week', 'week_start_date'),
        {'comment': 'Pagos semanales COD de transportistas. Se crean/actualizan '
                'automáticamente cuando\n'
                'se entrega o devuelve una orden. Cuando payment_status cambia a '
                '"paid", se crea\n'
                'una transacción financiera automáticamente.',
     'schema': 'operations'}
    )

    payment_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    carrier_id: Mapped[str] = mapped_column(String(20), nullable=False)
    week_start_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    week_end_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    payment_status: Mapped[Optional[str]] = mapped_column(Enum('pending', 'paid', name='payment_status', schema='operations'), server_default=text("'pending'::operations.payment_status"))
    payment_method: Mapped[Optional[str]] = mapped_column(Enum('cod', 'bank_transfer', 'qr', 'cash', 'crypto', name='payment_method', schema='operations'))
    received_in_wallet_id: Mapped[Optional[str]] = mapped_column(String(20))
    paid_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    total_deliveries: Mapped[Optional[int]] = mapped_column(Integer, server_default=text('0'), comment='Cantidad de órdenes entregadas en la semana')
    total_deliveries_amount: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(15, 2), server_default=text('0'), comment='Suma de (orden.total - comision_entrega) para entregas')
    total_returns: Mapped[Optional[int]] = mapped_column(Integer, server_default=text('0'), comment='Cantidad de órdenes devueltas en la semana')
    total_returns_amount: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(15, 2), server_default=text('0'), comment='Suma de comisiones de retorno')
    total_net_amount: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(15, 2), server_default=text('0'), comment='Saldo de ESTA semana únicamente: deliveries_amount - returns_amount')
    previous_balance: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(15, 2), server_default=text('0'), comment='Saldo arrastrado de la semana anterior (puede ser negativo si hubo más devoluciones)')
    total_final_amount: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(15, 2), server_default=text('0'), comment='Saldo TOTAL incluyendo anterior: total_net_amount + previous_balance')
    balance_status: Mapped[Optional[str]] = mapped_column(String(20), server_default=text("'pending'::character varying"), comment='Estado del saldo: pending | positive (puede pagarse) | negative (arrastra) | paid')

    carrier: Mapped['Carriers'] = relationship('Carriers', back_populates='payments')
    received_in_wallet: Mapped[Optional['Accounts']] = relationship('Accounts')
    payment_orders: Mapped[list['PaymentOrders']] = relationship('PaymentOrders', back_populates='payment')



class OrderItems(Base):
    __tablename__ = 'order_items'
    __table_args__ = (
        CheckConstraint("order_item_id::text ~ '^[A-Z]+[0-9]{8}-[0-9]+$'::text", name='check_order_item_id_format'),
        CheckConstraint('quantity > 0 AND unit_price >= 0::numeric AND subtotal >= 0::numeric', name='check_item_amounts'),
        ForeignKeyConstraint(['order_id'], ['operations.orders.order_id'], ondelete='CASCADE', name='order_items_order_id_fkey'),
        ForeignKeyConstraint(['product_variant_id'], ['product.product_variants.product_variant_id'], ondelete='RESTRICT', name='fk_order_items_variant'),
        PrimaryKeyConstraint('order_item_id', name='order_items_pkey'),
        Index('idx_order_items_order', 'order_id'),
        Index('idx_order_items_variant', 'product_variant_id'),
        {'comment': 'Items de cada orden. El subtotal se calcula al insertar (quantity '
                '* unit_price)\n'
                'y actualiza automáticamente el subtotal de la orden.',
     'schema': 'operations'}
    )

    order_item_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    order_id: Mapped[str] = mapped_column(String(20), nullable=False)
    product_variant_id: Mapped[str] = mapped_column(String(30), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[decimal.Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment='Precio unitario del producto (viene de Shopify). NO se autocalcula.')
    subtotal: Mapped[decimal.Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment='Total del item = quantity * unit_price (viene de Shopify). NO se autocalcula.')
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'), comment='Fecha de creación del item.')
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'), comment='Fecha de última actualización. Se actualiza automáticamente con trigger.')
    product_name: Mapped[Optional[str]] = mapped_column(String(200))

    order: Mapped['Orders'] = relationship('Orders', back_populates='order_items')
    product_variant: Mapped['ProductVariants'] = relationship('ProductVariants')


class OrderTracking(Base):
    __tablename__ = 'order_tracking'
    __table_args__ = (
        ForeignKeyConstraint(['order_id'], ['operations.orders.order_id'], ondelete='CASCADE', name='order_tracking_order_id_fkey'),
        PrimaryKeyConstraint('order_id', name='order_tracking_pkey'),
        Index('idx_tracking_status', 'order_status'),
        {'comment': 'Tracking 1-to-1 con orders. Cambios en order_status disparan '
                'múltiples efectos:\n'
                '- "delivered" → crea inventory_movement y decrementa stock\n'
                '- Cambio desde "delivered" → DELETE inventory_movement y restaura '
                'stock\n'
                '- "delivered" o "returned" → actualiza/crea payment semanal',
     'schema': 'operations'}
    )

    order_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    order_status: Mapped[str] = mapped_column(Enum('new', 'confirmed', 'in_transit', 'delivered', 'returned', 'cancelled', 'rescheduled', 'novelty', 'no_report', 'no_stock', 'dispatched', name='order_status', schema='operations'), nullable=False, server_default=text("'new'::operations.order_status"))
    tracking_code: Mapped[Optional[str]] = mapped_column(String(100))
    status_notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    reminder_1h: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('false'))
    reminder_2h: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('false'))
    reminder_3h: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('false'))
    followup_1_9am: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('false'))
    followup_1_8pm: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('false'))
    followup_2_days: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('false'))
    followup_3_days: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('false'))
    followup_rescheduled: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('false'))
    followup_no_stock: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('false'))
    followup_delivered: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('false'))
    followup_cancelled: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('false'))
    dispatched: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('false'))
    chat_paused: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('false'))
    daily_notes: Mapped[Optional[dict]] = mapped_column(JSON, comment='JSON structure: {"day_1": {"status": "", "nota": "", "date": "dd/mm/yyyy"}, "day_2": {...}, ...}')

    # Relación 1-to-1 con Orders
    order: Mapped['Orders'] = relationship('Orders', back_populates='tracking', uselist=False)


class PaymentOrders(Base):
    __tablename__ = 'payment_orders'
    __table_args__ = (
        CheckConstraint("contribution_type::text = ANY (ARRAY['delivery'::character varying, 'return'::character varying]::text[])", name='check_contribution_type'),
        ForeignKeyConstraint(['order_id'], ['operations.orders.order_id'], ondelete='CASCADE', name='fk_payment_orders_order'),
        ForeignKeyConstraint(['payment_id'], ['operations.payments.payment_id'], ondelete='CASCADE', name='fk_payment_orders_payment'),
        PrimaryKeyConstraint('payment_order_id', name='payment_orders_pkey'),
        UniqueConstraint('payment_id', 'order_id', 'contribution_type', name='unique_payment_order'),
        Index('idx_payment_orders_order', 'order_id'),
        Index('idx_payment_orders_payment', 'payment_id'),
        Index('idx_payment_orders_type', 'contribution_type'),
        {'comment': 'Tabla de relación que registra qué órdenes específicas '
                'contribuyen a cada pago semanal',
     'schema': 'operations'}
    )

    payment_order_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    payment_id: Mapped[str] = mapped_column(String(20), nullable=False)
    order_id: Mapped[str] = mapped_column(String(20), nullable=False)
    contribution_type: Mapped[str] = mapped_column(String(20), nullable=False, comment='Tipo de contribución: delivery (merchant recibe) o return (merchant paga)')
    amount_contributed: Mapped[decimal.Decimal] = mapped_column(Numeric(15, 2), nullable=False, comment='Monto que esta orden aporta:\n- delivery: (order_total - commission)\n- return: -commission (negativo)')
    order_total: Mapped[decimal.Decimal] = mapped_column(Numeric(15, 2), nullable=False, comment='Snapshot del total de la orden al momento de contribuir')
    commission_applied: Mapped[decimal.Decimal] = mapped_column(Numeric(15, 2), nullable=False, comment='Snapshot de la comisión aplicada (delivery o return según tipo)')
    added_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

    order: Mapped['Orders'] = relationship('Orders', back_populates='payment_orders')
    payment: Mapped['Payments'] = relationship('Payments', back_populates='payment_orders')
