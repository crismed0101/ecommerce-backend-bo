from typing import Optional
import datetime
import decimal

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Computed, DateTime, Enum, ForeignKeyConstraint, Index, Integer, Numeric, PrimaryKeyConstraint, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Cross-schema imports (lazy para evitar circular imports)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.finance_generated import Accounts
    from app.models.operations_generated import Orders

from app.core.database import Base




class Products(Base):
    __tablename__ = 'products'
    __table_args__ = (
        PrimaryKeyConstraint('product_id', name='products_pkey'),
        UniqueConstraint('product_name', name='products_product_name_key'),
        Index('idx_products_active', 'is_active'),
        Index('idx_products_category', 'category'),
        Index('idx_products_shopify_id', 'shopify_product_id'),
        {'comment': 'Catálogo de productos. Cada producto puede tener múltiples '
                'variantes\n'
                '(ej: diferentes colores, tamaños, versiones).\n'
                'product_name es UNIQUE - no se permiten productos duplicados con '
                'el mismo nombre.',
     'schema': 'product'}
    )

    product_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(Enum('PRODUCTOS_PARA_BEBE', 'ROPA_Y_MODA', 'ELECTRONICA_Y_TECNOLOGIA', 'HOGAR_Y_COCINA', 'BELLEZA_Y_CUIDADO_PERSONAL', 'SALUD_Y_BIENESTAR', 'DEPORTES_Y_FITNESS', 'JUGUETES', 'LIBROS_Y_PAPELERIA', 'ACCESORIOS', 'CALZADO', 'ALIMENTOS_Y_BEBIDAS', 'MASCOTAS', 'AUTOMOTRIZ', 'HERRAMIENTAS', 'OTROS', name='product_category', schema='product'), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('true'))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    shopify_product_id: Mapped[Optional[int]] = mapped_column(BigInteger)

    product_variants: Mapped[list['ProductVariants']] = relationship('ProductVariants', back_populates='product')


class Suppliers(Base):
    __tablename__ = 'suppliers'
    __table_args__ = (
        CheckConstraint("bank_accounts IS NULL OR jsonb_typeof(bank_accounts) = 'object'::text", name='check_bank_accounts_structure'),
        CheckConstraint("contacts IS NULL OR jsonb_typeof(contacts) = 'object'::text", name='check_contacts_structure'),
        PrimaryKeyConstraint('supplier_id', name='suppliers_pkey'),
        UniqueConstraint('supplier_name', name='suppliers_supplier_name_key'),
        Index('idx_suppliers_active', 'is_active'),
        Index('idx_suppliers_city', 'city'),
        Index('idx_suppliers_country', 'country'),
        Index('idx_suppliers_name', 'supplier_name'),
        Index('idx_suppliers_tax_id', 'tax_id'),
        {'schema': 'product'}
    )

    supplier_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    supplier_name: Mapped[str] = mapped_column(String(200), nullable=False)
    contacts: Mapped[Optional[dict]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('true'))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    tax_id: Mapped[Optional[str]] = mapped_column(String(50))
    country: Mapped[Optional[str]] = mapped_column(String(100))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    address: Mapped[Optional[str]] = mapped_column(Text)
    bank_accounts: Mapped[Optional[dict]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    default_currency: Mapped[Optional[str]] = mapped_column(Enum('BOB', 'USD', 'USDT', 'USDC', 'EUR', 'CNY', 'PEN', 'ARS', 'COP', 'PYG', 'BRL', name='currency_code', schema='finance'), server_default=text("'BOB'::finance.currency_code"))

    purchases: Mapped[list['Purchases']] = relationship('Purchases', back_populates='supplier')



class ProductVariants(Base):
    __tablename__ = 'product_variants'
    __table_args__ = (
        ForeignKeyConstraint(['product_id'], ['product.products.product_id'], ondelete='RESTRICT', name='product_variants_product_id_fkey'),
        PrimaryKeyConstraint('product_variant_id', name='product_variants_pkey'),
        UniqueConstraint('product_id', 'variant_name', name='unique_product_variant_name'),
        UniqueConstraint('sku', name='product_variants_sku_key'),
        Index('idx_variants_active', 'is_active'),
        Index('idx_variants_product', 'product_id'),
        Index('idx_variants_shopify_id', 'shopify_variant_id'),
        Index('idx_variants_sku', 'sku'),
        {'comment': 'Variantes de productos. product_variant_id usa formato '
                'PROD00001-V01 (vinculado al product_id).\n'
                'Este ID se usa en order_items e inventory.\n'
                'Validaciones:\n'
                '- UNIQUE (product_id, variant_name): No permite variantes '
                'duplicadas para el mismo producto\n'
                '- CHECK selling_price >= cost_price: No permite vender a pérdida '
                '(si cost_price está definido)',
     'schema': 'product'}
    )

    product_variant_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    product_id: Mapped[str] = mapped_column(String(20), nullable=False)
    variant_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('true'))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    attributes: Mapped[Optional[dict]] = mapped_column(JSONB)
    sku: Mapped[Optional[str]] = mapped_column(String(100))
    shopify_variant_id: Mapped[Optional[int]] = mapped_column(BigInteger)

    product: Mapped['Products'] = relationship('Products', back_populates='product_variants')
    inventory: Mapped[list['Inventory']] = relationship('Inventory', back_populates='product_variant')
    inventory_movements: Mapped[list['InventoryMovements']] = relationship('InventoryMovements', back_populates='product_variant')
    purchase_items: Mapped[list['PurchaseItems']] = relationship('PurchaseItems', back_populates='product_variant')


class Purchases(Base):
    __tablename__ = 'purchases'
    __table_args__ = (
        CheckConstraint('total_cost > 0::numeric', name='check_total_cost_positive'),
        ForeignKeyConstraint(['payment_account_id'], ['finance.accounts.account_id'], ondelete='RESTRICT', name='purchases_payment_account_id_fkey'),
        ForeignKeyConstraint(['supplier_id'], ['product.suppliers.supplier_id'], ondelete='RESTRICT', name='fk_purchases_supplier'),
        PrimaryKeyConstraint('purchase_id', name='purchases_pkey'),
        Index('idx_purchases_account', 'payment_account_id'),
        Index('idx_purchases_date', 'purchase_date'),
        Index('idx_purchases_status', 'status'),
        Index('idx_purchases_supplier', 'supplier_id'),
        {'comment': 'Compras de inventario a proveedores. Cada compra puede tener '
                'múltiples items\n'
                '(purchase_items) y genera transacción financiera automáticamente.',
     'schema': 'product'}
    )

    purchase_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    purchase_date: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    total_cost: Mapped[decimal.Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(Enum('BOB', 'USD', 'USDT', 'USDC', 'EUR', 'CNY', 'PEN', 'ARS', 'COP', 'PYG', 'BRL', name='currency_code', schema='finance'), nullable=False)
    supplier_id: Mapped[str] = mapped_column(String(20), nullable=False)
    payment_account_id: Mapped[Optional[str]] = mapped_column(String(20))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    total_quantity: Mapped[Optional[int]] = mapped_column(Integer, server_default=text('0'))
    status: Mapped[Optional[str]] = mapped_column(Enum('pending', 'received', 'cancelled', name='purchase_status', schema='product'), server_default=text("'received'::product.purchase_status"))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

    payment_account: Mapped[Optional['Accounts']] = relationship('Accounts')
    supplier: Mapped['Suppliers'] = relationship('Suppliers', back_populates='purchases')
    inventory_movements: Mapped[list['InventoryMovements']] = relationship('InventoryMovements', back_populates='purchase')
    purchase_items: Mapped[list['PurchaseItems']] = relationship('PurchaseItems', back_populates='purchase')


class Inventory(Base):
    __tablename__ = 'inventory'
    __table_args__ = (
        CheckConstraint('stock_quantity >= 0', name='check_stock_not_negative'),
        ForeignKeyConstraint(['product_variant_id'], ['product.product_variants.product_variant_id'], ondelete='RESTRICT', name='inventory_product_variant_id_fkey'),
        PrimaryKeyConstraint('inventory_id', name='inventory_pkey'),
        UniqueConstraint('product_variant_id', 'department', name='unique_variant_department'),
        Index('idx_inventory_availability', 'product_variant_id', 'department', 'stock_quantity'),
        Index('idx_inventory_department', 'department'),
        Index('idx_inventory_updated', 'updated_at'),
        Index('idx_inventory_variant', 'product_variant_id'),
        {'comment': 'Inventario por variante y departamento. quantity_available se '
                'actualiza automáticamente:\n'
                '- Incrementa con purchases\n'
                '- Decrementa cuando order_status = "delivered"\n'
                '- Restaura cuando se revierte una entrega',
     'schema': 'product'}
    )

    inventory_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    product_variant_id: Mapped[str] = mapped_column(String(20), nullable=False)
    department: Mapped[str] = mapped_column(Enum('LA PAZ', 'COCHABAMBA', 'SANTA CRUZ', 'ORURO', 'POTOSI', 'TARIJA', 'CHUQUISACA', 'BENI', 'PANDO', name='department_stock', schema='product'), nullable=False)
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

    product_variant: Mapped['ProductVariants'] = relationship('ProductVariants', back_populates='inventory')


class InventoryMovements(Base):
    __tablename__ = 'inventory_movements'
    __table_args__ = (
        CheckConstraint("movement_type = 'purchase'::product.movement_type AND purchase_id IS NOT NULL AND order_id IS NULL OR movement_type <> 'purchase'::product.movement_type", name='check_purchase_reference'),
        CheckConstraint("movement_type = 'transfer'::product.movement_type AND department_origin <> department_destination OR movement_type <> 'transfer'::product.movement_type AND department_origin = department_destination", name='check_departments_logic'),
        CheckConstraint("movement_type = ANY (ARRAY['sale'::product.movement_type, 'return'::product.movement_type])) AND order_id IS NOT NULL AND purchase_id IS NULL OR (movement_type <> ALL (ARRAY['sale'::product.movement_type, 'return'::product.movement_type])", name='check_sale_return_order'),
        CheckConstraint("movement_type = ANY (ARRAY['transfer'::product.movement_type, 'adjustment_positive'::product.movement_type, 'adjustment_negative'::product.movement_type])) AND order_id IS NULL AND purchase_id IS NULL OR (movement_type <> ALL (ARRAY['transfer'::product.movement_type, 'adjustment_positive'::product.movement_type, 'adjustment_negative'::product.movement_type])", name='check_no_reference_ids'),
        CheckConstraint('quantity > 0', name='check_quantity_positive'),
        ForeignKeyConstraint(['order_id'], ['operations.orders.order_id'], ondelete='RESTRICT', name='fk_movements_order'),
        ForeignKeyConstraint(['product_variant_id'], ['product.product_variants.product_variant_id'], ondelete='RESTRICT', name='inventory_movements_product_variant_id_fkey'),
        ForeignKeyConstraint(['purchase_id'], ['product.purchases.purchase_id'], ondelete='RESTRICT', name='fk_movements_purchase'),
        PrimaryKeyConstraint('movement_id', name='inventory_movements_pkey'),
        Index('idx_movements_date', 'created_at'),
        Index('idx_movements_department', 'department_origin'),
        Index('idx_movements_order', 'order_id'),
        Index('idx_movements_purchase', 'purchase_id'),
        Index('idx_movements_type_date', 'movement_type', 'created_at'),
        Index('idx_movements_variant', 'product_variant_id'),
        {'comment': 'Historial de movimientos de inventario. Los movimientos tipo '
                '"sale" se crean automáticamente\n'
                'cuando order_status = "delivered" y se ELIMINAN (no reversan) si '
                'se cambia a otro estado.',
     'schema': 'product'}
    )

    movement_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    product_variant_id: Mapped[str] = mapped_column(String(20), nullable=False)
    department_origin: Mapped[str] = mapped_column(Enum('LA PAZ', 'COCHABAMBA', 'SANTA CRUZ', 'ORURO', 'POTOSI', 'TARIJA', 'CHUQUISACA', 'BENI', 'PANDO', name='department_stock', schema='product'), nullable=False)
    movement_type: Mapped[str] = mapped_column(Enum('purchase', 'sale', 'adjustment', 'return', 'transfer', 'adjustment_positive', 'adjustment_negative', name='movement_type', schema='product'), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    department_destination: Mapped[str] = mapped_column(Enum('LA PAZ', 'COCHABAMBA', 'SANTA CRUZ', 'ORURO', 'POTOSI', 'TARIJA', 'CHUQUISACA', 'BENI', 'PANDO', name='department_stock', schema='product'), nullable=False)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    order_id: Mapped[Optional[str]] = mapped_column(String(20), server_default=text('NULL::character varying'))
    purchase_id: Mapped[Optional[str]] = mapped_column(String(20), server_default=text('NULL::character varying'))

    order: Mapped[Optional['Orders']] = relationship('Orders')
    product_variant: Mapped['ProductVariants'] = relationship('ProductVariants', back_populates='inventory_movements')
    purchase: Mapped[Optional['Purchases']] = relationship('Purchases', back_populates='inventory_movements')


class PurchaseItems(Base):
    __tablename__ = 'purchase_items'
    __table_args__ = (
        ForeignKeyConstraint(['product_variant_id'], ['product.product_variants.product_variant_id'], ondelete='RESTRICT', name='purchase_items_product_variant_id_fkey'),
        ForeignKeyConstraint(['purchase_id'], ['product.purchases.purchase_id'], ondelete='CASCADE', name='purchase_items_purchase_id_fkey'),
        PrimaryKeyConstraint('purchase_id', 'product_variant_id', 'department', name='purchase_items_pkey'),
        Index('idx_purchase_items_department', 'department'),
        Index('idx_purchase_items_variant', 'product_variant_id'),
        {'comment': 'Items de cada compra. Incrementa automáticamente el inventario '
                'del departamento\n'
                'correspondiente al insertar.',
     'schema': 'product'}
    )

    purchase_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    product_variant_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    department: Mapped[str] = mapped_column(Enum('LA PAZ', 'COCHABAMBA', 'SANTA CRUZ', 'ORURO', 'POTOSI', 'TARIJA', 'CHUQUISACA', 'BENI', 'PANDO', name='department_stock', schema='product'), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[decimal.Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    subtotal: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(10, 2), Computed('((quantity)::numeric * unit_cost)', persisted=True))

    product_variant: Mapped['ProductVariants'] = relationship('ProductVariants', back_populates='purchase_items')
    purchase: Mapped['Purchases'] = relationship('Purchases', back_populates='purchase_items')
