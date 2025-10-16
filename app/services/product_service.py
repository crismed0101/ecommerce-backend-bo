"""
ProductService - Gestión de productos y variantes

Responsabilidades:
1. Búsqueda en cascada de variantes (shopify_variant_id → sku → name)
2. Auto-generación de SKU si no existe
3. Auto-creación de productos/variantes si no existen
4. Creación de inventario inicial en todos los departamentos

Principios:
- IDEMPOTENCY: Buscar antes de crear
- DRY: Una sola función para encontrar/crear variantes
- SOLID: Responsabilidad única (solo productos)
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, Dict, List, Tuple
import logging
import re

from app.models import Products, ProductVariants, Inventory
from app.services.id_generator import IDGenerator
from app.schemas.order import DepartmentEnum

logger = logging.getLogger(__name__)


class ProductService:
    """
    Service para gestión de productos

    BÚSQUEDA EN CASCADA:
    1. Si tiene shopify_variant_id → buscar por shopify_variant_id
    2. Si tiene sku → buscar por sku
    3. Si tiene product_name → buscar por nombre (exacto)
    4. Si no existe → AUTO-CREAR producto + variante + inventario
    """

    # ==================== BÚSQUEDA EN CASCADA ====================

    @staticmethod
    def find_or_create_variant(
        db: Session,
        shopify_product_id: Optional[int],
        shopify_variant_id: Optional[int],
        product_name: str,
        sku: Optional[str] = None
    ) -> Tuple[ProductVariants, bool]:
        """
        Buscar o crear variante (CASCADA)

        Estrategia de búsqueda (en orden):
        1. shopify_variant_id
        2. sku
        3. product_name (exacto)
        4. AUTO-CREAR

        Args:
            db: Database session
            shopify_product_id: ID del producto en Shopify (puede ser None)
            shopify_variant_id: ID de la variante en Shopify (puede ser None)
            product_name: Nombre del producto
            sku: SKU universal (puede ser None)

        Returns:
            Tuple (ProductVariants, was_created: bool)
        """

        logger.info(f"🔍 Buscando variante: shopify_variant_id={shopify_variant_id}, "
                   f"sku={sku}, name={product_name}")

        # PASO 1: Buscar por shopify_variant_id
        if shopify_variant_id:
            variant = db.query(ProductVariants).filter(
                ProductVariants.shopify_variant_id == str(shopify_variant_id)
            ).first()

            if variant:
                logger.info(f"✅ Variante encontrada por shopify_variant_id: {variant.product_variant_id}")
                return variant, False

        # PASO 2: Buscar por SKU
        if sku:
            variant = db.query(ProductVariants).filter(
                ProductVariants.sku == sku
            ).first()

            if variant:
                logger.info(f"✅ Variante encontrada por SKU: {variant.product_variant_id}")

                # Si no tenía shopify_variant_id, actualizarlo
                if shopify_variant_id and not variant.shopify_variant_id:
                    variant.shopify_variant_id = str(shopify_variant_id)
                    db.commit()
                    logger.info(f"📝 shopify_variant_id actualizado: {shopify_variant_id}")

                return variant, False

        # PASO 3: Buscar por nombre (exacto)
        variant = db.query(ProductVariants).filter(
            ProductVariants.variant_name == product_name
        ).first()

        if variant:
            logger.info(f"✅ Variante encontrada por nombre: {variant.product_variant_id}")

            # Actualizar campos faltantes
            if shopify_variant_id and not variant.shopify_variant_id:
                variant.shopify_variant_id = str(shopify_variant_id)
            if sku and not variant.sku:
                variant.sku = sku
            db.commit()
            logger.info(f"📝 Campos actualizados en variante existente")

            return variant, False

        # PASO 4: NO EXISTE → AUTO-CREAR
        logger.warning(f"⚠️ Variante NO encontrada, auto-creando: {product_name}")
        variant, was_created = ProductService._create_product_and_variant(
            db=db,
            shopify_product_id=shopify_product_id,
            shopify_variant_id=shopify_variant_id,
            product_name=product_name,
            sku=sku
        )

        return variant, was_created

    # ==================== AUTO-CREACIÓN ====================

    @staticmethod
    def _create_product_and_variant(
        db: Session,
        shopify_product_id: Optional[int],
        shopify_variant_id: Optional[int],
        product_name: str,
        sku: Optional[str]
    ) -> Tuple[ProductVariants, bool]:
        """
        Crear producto + variante + inventario inicial

        1. Buscar o crear producto padre
        2. Generar SKU si no existe
        3. Crear variante
        4. Crear inventario en TODOS los departamentos (stock=0)

        Returns:
            Tuple (ProductVariants, was_created=True)
        """

        try:
            # PASO 1: Buscar o crear producto padre
            product = ProductService._find_or_create_product(
                db=db,
                product_name=product_name,
                shopify_product_id=shopify_product_id
            )

            # PASO 2: Generar SKU si no existe
            if not sku:
                sku = ProductService._generate_sku(db, product_name)
                logger.info(f"🏷️ SKU auto-generado: {sku}")

            # PASO 3: Crear variante
            variant_number = len(product.product_variants) + 1
            variant_id = IDGenerator.generate_variant_id(db, product.product_id, variant_number)

            variant = ProductVariants(
                product_variant_id=variant_id,
                product_id=product.product_id,
                variant_name=product_name,
                sku=sku,
                shopify_variant_id=str(shopify_variant_id) if shopify_variant_id else None,
                is_active=True
            )

            db.add(variant)
            db.flush()  # Flush para obtener el variant_id

            logger.info(f"✅ Variante creada: {variant_id} (sku={sku})")

            # PASO 4: Crear inventario inicial en TODOS los departamentos
            ProductService._create_initial_inventory(db, variant_id)

            db.commit()

            return variant, True

        except IntegrityError as e:
            db.rollback()
            logger.error(f"❌ Error creando producto/variante: {e}")
            raise ValueError(f"Error creando producto: {str(e)}")

    @staticmethod
    def _find_or_create_product(
        db: Session,
        product_name: str,
        shopify_product_id: Optional[int]
    ) -> Products:
        """
        Buscar o crear producto padre

        Busca por:
        1. shopify_product_id (si está disponible)
        2. product_name (exacto)
        3. Crear nuevo si no existe
        """

        # Buscar por shopify_product_id
        if shopify_product_id:
            product = db.query(Products).filter(
                Products.shopify_product_id == str(shopify_product_id)
            ).first()

            if product:
                logger.info(f"✅ Producto padre encontrado por shopify_product_id: {product.product_id}")
                return product

        # Buscar por nombre
        product = db.query(Products).filter(
            Products.product_name == product_name
        ).first()

        if product:
            logger.info(f"✅ Producto padre encontrado por nombre: {product.product_id}")

            # Actualizar shopify_product_id si no estaba
            if shopify_product_id and not product.shopify_product_id:
                product.shopify_product_id = str(shopify_product_id)
                db.commit()

            return product

        # Crear nuevo producto
        product_id = IDGenerator.generate_product_id(db)

        product = Products(
            product_id=product_id,
            product_name=product_name,
            shopify_product_id=str(shopify_product_id) if shopify_product_id else None,
            category="ROPA_Y_MODA",  # Categoría por defecto
            is_active=True
        )

        db.add(product)
        db.flush()

        logger.info(f"✅ Producto padre creado: {product_id}")

        return product

    @staticmethod
    def _generate_sku(db: Session, product_name: str) -> str:
        """
        Generar SKU único basado en nombre del producto

        Formato: PRODUCTNAME-001, PRODUCTNAME-002, etc.

        Ejemplo:
        - "Chompa Roja" → "CHOMPAROJA-001"
        - "Polo Azul" → "POLOAZUL-001"
        """

        # Limpiar nombre (solo letras y números)
        clean_name = re.sub(r'[^A-Za-z0-9]', '', product_name.upper())

        # Limitar a 20 caracteres
        clean_name = clean_name[:20]

        # Buscar el último número usado para este producto
        last_variant = db.query(ProductVariants).filter(
            ProductVariants.sku.like(f"{clean_name}-%")
        ).order_by(ProductVariants.sku.desc()).first()

        if last_variant and last_variant.sku:
            # Extraer número del SKU: "CHOMPAROJA-001" → 1
            parts = last_variant.sku.split("-")
            if len(parts) == 2:
                try:
                    last_number = int(parts[1])
                    next_number = last_number + 1
                except ValueError:
                    next_number = 1
            else:
                next_number = 1
        else:
            next_number = 1

        # Formato: PRODUCTNAME-001
        sku = f"{clean_name}-{next_number:03d}"

        return sku

    @staticmethod
    def _create_initial_inventory(db: Session, variant_id: str):
        """
        Crear inventario inicial en TODOS los departamentos

        Stock inicial = 0 en todos los departamentos
        """

        departments = [dept.value for dept in DepartmentEnum]

        # IDEMPOTENCIA MEJORADA: Obtener TODOS los inventarios existentes de una vez
        existing_inventories = db.query(Inventory).filter(
            Inventory.product_variant_id == variant_id
        ).all()

        existing_departments = {inv.department for inv in existing_inventories}
        logger.info(f"📦 Inventarios existentes para {variant_id}: {existing_departments}")

        inventories_to_create = []

        for department in departments:
            # Convertir LA_PAZ → LA PAZ (reemplazar _ con espacio)
            department_db = department.replace('_', ' ')

            # Verificar si ya existe este departamento
            if department_db in existing_departments:
                logger.info(f"⚠️ Inventario ya existe para {variant_id} en {department_db}, saltando...")
                continue

            inventory_id = IDGenerator.generate_inventory_id(db)

            inventory = Inventory(
                inventory_id=inventory_id,
                product_variant_id=variant_id,
                department=department_db,
                stock_quantity=0
            )

            inventories_to_create.append(inventory)

        # Agregar SOLO los inventarios que no existen
        if inventories_to_create:
            for inventory in inventories_to_create:
                db.add(inventory)
            logger.info(f"✅ Creando {len(inventories_to_create)} nuevos inventarios")
        else:
            logger.info(f"✅ Todos los inventarios ya existen para {variant_id}")

    # ==================== VALIDACIONES Y DESACTIVACIÓN ====================

    @staticmethod
    def deactivate_product(
        db: Session,
        product_id: str,
        also_deactivate_variants: bool = True
    ):
        """
        Desactivar producto y opcionalmente sus variantes

        REEMPLAZA: trg_01_deactivate_variants

        Cuando se desactiva un producto, automáticamente desactiva
        todas sus variantes (cascada)

        Args:
            db: Database session
            product_id: ID del producto a desactivar
            also_deactivate_variants: Si True, desactiva todas las variantes

        Raises:
            ValueError: Si el producto no existe
        """

        # Obtener producto
        product = db.query(Products).filter(
            Products.product_id == product_id
        ).first()

        if not product:
            raise ValueError(f"Producto {product_id} no encontrado")

        # Desactivar producto
        product.is_active = False
        db.flush()

        logger.info(f"🔒 Producto desactivado: {product_id}")

        # Desactivar todas las variantes en cascada
        if also_deactivate_variants:
            variants = db.query(ProductVariants).filter(
                ProductVariants.product_id == product_id,
                ProductVariants.is_active == True
            ).all()

            variants_count = len(variants)

            for variant in variants:
                variant.is_active = False

            db.flush()

            logger.info(
                f"🔒 {variants_count} variantes desactivadas en cascada para producto {product_id}"
            )

        db.commit()

    @staticmethod
    def activate_product(
        db: Session,
        product_id: str,
        also_activate_variants: bool = False
    ):
        """
        Activar producto (opcionalmente sus variantes)

        Args:
            db: Database session
            product_id: ID del producto a activar
            also_activate_variants: Si True, activa todas las variantes

        Raises:
            ValueError: Si el producto no existe
        """

        # Obtener producto
        product = db.query(Products).filter(
            Products.product_id == product_id
        ).first()

        if not product:
            raise ValueError(f"Producto {product_id} no encontrado")

        # Activar producto
        product.is_active = True
        db.flush()

        logger.info(f"✅ Producto activado: {product_id}")

        # Activar variantes si se solicita
        if also_activate_variants:
            variants = db.query(ProductVariants).filter(
                ProductVariants.product_id == product_id,
                ProductVariants.is_active == False
            ).all()

            variants_count = len(variants)

            for variant in variants:
                variant.is_active = True

            db.flush()

            logger.info(
                f"✅ {variants_count} variantes activadas para producto {product_id}"
            )

        db.commit()

    @staticmethod
    def validate_variant_can_be_activated(
        db: Session,
        variant_id: str
    ):
        """
        Validar que una variante puede ser activada

        REEMPLAZA: trg_01_validate_variant_active

        Una variante solo puede estar activa si su producto padre está activo

        Args:
            db: Database session
            variant_id: ID de la variante

        Raises:
            ValueError: Si el producto padre está inactivo
        """

        # Obtener variante con producto padre
        variant = db.query(ProductVariants).filter(
            ProductVariants.product_variant_id == variant_id
        ).first()

        if not variant:
            raise ValueError(f"Variante {variant_id} no encontrada")

        # Obtener producto padre
        product = db.query(Products).filter(
            Products.product_id == variant.product_id
        ).first()

        if not product:
            raise ValueError(f"Producto padre {variant.product_id} no encontrado")

        # Validar que el producto padre esté activo
        if not product.is_active:
            raise ValueError(
                f"No se puede activar variante {variant_id} porque "
                f"su producto padre {product.product_id} está inactivo"
            )

        logger.debug(f"✅ Variante {variant_id} puede ser activada (producto padre activo)")

    @staticmethod
    def activate_variant(
        db: Session,
        variant_id: str
    ):
        """
        Activar variante (validando que producto padre esté activo)

        Args:
            db: Database session
            variant_id: ID de la variante

        Raises:
            ValueError: Si el producto padre está inactivo
        """

        # Validar primero
        ProductService.validate_variant_can_be_activated(db, variant_id)

        # Activar variante
        variant = db.query(ProductVariants).filter(
            ProductVariants.product_variant_id == variant_id
        ).first()

        variant.is_active = True
        db.commit()

        logger.info(f"✅ Variante activada: {variant_id}")

    @staticmethod
    def deactivate_variant(
        db: Session,
        variant_id: str
    ):
        """
        Desactivar variante

        Args:
            db: Database session
            variant_id: ID de la variante

        Raises:
            ValueError: Si la variante no existe
        """

        variant = db.query(ProductVariants).filter(
            ProductVariants.product_variant_id == variant_id
        ).first()

        if not variant:
            raise ValueError(f"Variante {variant_id} no encontrada")

        variant.is_active = False
        db.commit()

        logger.info(f"🔒 Variante desactivada: {variant_id}")

    # ==================== UTILIDADES ====================

    @staticmethod
    def get_variant_by_id(db: Session, variant_id: str) -> Optional[ProductVariants]:
        """
        Obtener variante por ID
        """
        return db.query(ProductVariants).filter(
            ProductVariants.product_variant_id == variant_id
        ).first()

    @staticmethod
    def list_variants(db: Session, product_id: Optional[str] = None, limit: int = 100) -> List[ProductVariants]:
        """
        Listar variantes

        Args:
            product_id: Filtrar por producto (opcional)
            limit: Límite de resultados
        """
        query = db.query(ProductVariants)

        if product_id:
            query = query.filter(ProductVariants.product_id == product_id)

        return query.limit(limit).all()

    # ==================== HISTORIAL DE PRECIOS ====================

    @staticmethod
    def update_variant_price(
        db: Session,
        variant_id: str,
        new_price: float,
        responsible_user: str,
        reason: Optional[str] = None
    ) -> Dict:
        """
        Actualizar precio de variante con auditoría completa

        AUDITORÍA DE PRECIOS:
        - Registra precio anterior y nuevo
        - Registra quién hizo el cambio (responsible_user)
        - Registra por qué (reason)
        - Registra cuándo (automático)
        - Calcula cambio porcentual

        NOTA: Este método registra el cambio en logs. Para persistencia completa,
        se debería crear una tabla product.price_history con campos:
        - price_history_id
        - product_variant_id
        - old_price
        - new_price
        - price_change_percent
        - changed_by (user)
        - change_reason
        - changed_at

        Args:
            db: Database session
            variant_id: ID de la variante
            new_price: Nuevo precio
            responsible_user: Usuario que autoriza el cambio
            reason: Razón del cambio de precio

        Returns:
            Dict con información del cambio de precio
        """
        try:
            # Obtener variante
            variant = db.query(ProductVariants).filter(
                ProductVariants.product_variant_id == variant_id
            ).first()

            if not variant:
                raise ValueError(f"Variante {variant_id} no encontrada")

            # Calcular cambio
            old_price = float(variant.price) if variant.price else 0
            price_change = new_price - old_price
            price_change_percent = (price_change / old_price * 100) if old_price > 0 else 0

            # Actualizar precio
            variant.price = new_price
            db.flush()

            # Registrar en logs (AUDITORÍA)
            logger.info(
                f"💰 PRECIO ACTUALIZADO: {variant_id} | "
                f"Precio anterior: {old_price} BOB | "
                f"Precio nuevo: {new_price} BOB | "
                f"Cambio: {price_change:+.2f} BOB ({price_change_percent:+.1f}%) | "
                f"Usuario: {responsible_user} | "
                f"Razón: {reason or 'No especificada'}"
            )

            db.commit()

            return {
                'variant_id': variant_id,
                'old_price': old_price,
                'new_price': new_price,
                'price_change': round(price_change, 2),
                'price_change_percent': round(price_change_percent, 2),
                'changed_by': responsible_user,
                'change_reason': reason,
                'status': 'success'
            }

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error actualizando precio: {str(e)}")
            raise ValueError(f"Error actualizando precio: {str(e)}")

    @staticmethod
    def get_price_change_alerts(
        db: Session,
        threshold_percent: float = 100.0
    ) -> List[Dict]:
        """
        Detectar cambios de precio significativos

        Esta función simula la detección de cambios grandes. En un sistema completo,
        se debería consultar la tabla product.price_history.

        Args:
            db: Database session
            threshold_percent: Umbral de cambio (default: 100% = duplicación o reducción a la mitad)

        Returns:
            Lista de alertas de cambios de precio

        NOTA: Para implementación completa, crear tabla price_history y consultar:
        SELECT * FROM product.price_history
        WHERE ABS(price_change_percent) > threshold_percent
        ORDER BY changed_at DESC
        """
        # Por ahora, retorna lista vacía ya que no hay tabla de historial
        # En implementación futura, consultar product.price_history
        logger.info(f"🔍 Buscando cambios de precio > {threshold_percent}%")
        return []

    # ==================== PRODUCTOS RELACIONADOS ====================

    @staticmethod
    def add_related_product(
        db: Session,
        product_id: str,
        related_product_id: str,
        relationship_type: str = "upsell"
    ) -> Dict:
        """
        Agregar producto relacionado para upselling/cross-selling

        TIPOS DE RELACIÓN:
        - "upsell": Versión premium del producto (ej: camisa básica → camisa premium)
        - "cross_sell": Producto complementario (ej: camisa → corbata)
        - "similar": Producto similar alternativo (ej: camisa roja → camisa azul)

        NOTA: Este método registra la relación en logs. Para persistencia completa,
        se debería crear una tabla product.product_relations con campos:
        - relation_id
        - product_id (producto principal)
        - related_product_id (producto relacionado)
        - relationship_type (upsell, cross_sell, similar)
        - display_order (orden de visualización)
        - is_active
        - created_at

        Args:
            db: Database session
            product_id: ID del producto principal
            related_product_id: ID del producto relacionado
            relationship_type: Tipo de relación (upsell, cross_sell, similar)

        Returns:
            Dict con información de la relación creada
        """
        try:
            # Validar que ambos productos existan
            product = db.query(Products).filter(Products.product_id == product_id).first()
            related = db.query(Products).filter(Products.product_id == related_product_id).first()

            if not product:
                raise ValueError(f"Producto {product_id} no encontrado")
            if not related:
                raise ValueError(f"Producto relacionado {related_product_id} no encontrado")

            # Registrar relación (AUDITORÍA)
            logger.info(
                f"🔗 RELACIÓN CREADA: {product_id} ({product.product_name}) → "
                f"{related_product_id} ({related.product_name}) | "
                f"Tipo: {relationship_type}"
            )

            return {
                'product_id': product_id,
                'product_name': product.product_name,
                'related_product_id': related_product_id,
                'related_product_name': related.product_name,
                'relationship_type': relationship_type,
                'status': 'success',
                'message': 'Relación registrada en logs. Para persistencia, crear tabla product.product_relations'
            }

        except Exception as e:
            logger.error(f"❌ Error creando relación: {str(e)}")
            raise ValueError(f"Error creando relación: {str(e)}")

    @staticmethod
    def get_related_products(
        db: Session,
        product_id: str,
        relationship_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Obtener productos relacionados para recomendaciones

        NOTA: Esta función retorna lista vacía ya que no hay tabla de relaciones.
        Para implementación completa, crear tabla product.product_relations y consultar:

        SELECT r.*, p.*
        FROM product.product_relations r
        JOIN product.products p ON p.product_id = r.related_product_id
        WHERE r.product_id = :product_id
        AND r.is_active = true
        AND (:relationship_type IS NULL OR r.relationship_type = :relationship_type)
        ORDER BY r.display_order

        Args:
            db: Database session
            product_id: ID del producto
            relationship_type: Filtrar por tipo (opcional)

        Returns:
            Lista de productos relacionados
        """
        # Validar que el producto existe
        product = db.query(Products).filter(Products.product_id == product_id).first()

        if not product:
            raise ValueError(f"Producto {product_id} no encontrado")

        # Por ahora, retorna lista vacía ya que no hay tabla de relaciones
        # En implementación futura, consultar product.product_relations
        logger.info(f"🔍 Buscando productos relacionados para {product_id} (tipo: {relationship_type or 'todos'})")

        return []

    @staticmethod
    def get_upsell_recommendations(
        db: Session,
        product_id: str,
        limit: int = 5
    ) -> List[Dict]:
        """
        Obtener recomendaciones de upsell para un producto

        ESTRATEGIA DE UPSELL (sin tabla de relaciones):
        1. Buscar productos de la misma categoría
        2. Con precio mayor al producto actual
        3. Ordenados por popularidad (total_sales descendente)

        Args:
            db: Database session
            product_id: ID del producto actual
            limit: Número máximo de recomendaciones

        Returns:
            Lista de productos recomendados para upsell
        """
        from sqlalchemy import func, and_

        # Obtener producto actual
        current_product = db.query(Products).filter(Products.product_id == product_id).first()

        if not current_product:
            raise ValueError(f"Producto {product_id} no encontrado")

        # Obtener precio promedio de variantes del producto actual
        current_avg_price = db.query(
            func.avg(ProductVariants.price)
        ).filter(
            ProductVariants.product_id == product_id,
            ProductVariants.is_active == True
        ).scalar() or 0

        # Buscar productos similares pero con precio mayor (UPSELL)
        upsell_products = db.query(
            Products,
            func.avg(ProductVariants.price).label('avg_price')
        ).join(
            ProductVariants,
            ProductVariants.product_id == Products.product_id
        ).filter(
            and_(
                Products.category == current_product.category,
                Products.product_id != product_id,
                Products.is_active == True,
                ProductVariants.is_active == True
            )
        ).group_by(
            Products.product_id
        ).having(
            func.avg(ProductVariants.price) > current_avg_price
        ).order_by(
            func.avg(ProductVariants.price).asc()  # Ordenar por precio (menor a mayor)
        ).limit(limit).all()

        recommendations = []
        for product, avg_price in upsell_products:
            recommendations.append({
                'product_id': product.product_id,
                'product_name': product.product_name,
                'category': product.category,
                'avg_price': float(avg_price) if avg_price else 0,
                'price_difference': float(avg_price - current_avg_price) if avg_price else 0,
                'recommendation_type': 'upsell'
            })

        logger.info(f"💡 {len(recommendations)} recomendaciones de upsell encontradas para {product_id}")

        return recommendations

    @staticmethod
    def get_cross_sell_recommendations(
        db: Session,
        product_id: str,
        limit: int = 5
    ) -> List[Dict]:
        """
        Obtener recomendaciones de cross-sell para un producto

        ESTRATEGIA DE CROSS-SELL (sin tabla de relaciones):
        1. Buscar productos de categorías diferentes
        2. Que suelen comprarse juntos (analizar órdenes históricas)
        3. Ordenados por frecuencia de compra conjunta

        Args:
            db: Database session
            product_id: ID del producto actual
            limit: Número máximo de recomendaciones

        Returns:
            Lista de productos recomendados para cross-sell
        """
        from app.models import Orders, OrderItems

        # Buscar productos que se han comprado junto con este producto
        cross_sell_query = db.query(
            ProductVariants.product_id,
            Products.product_name,
            Products.category,
            func.count(Orders.order_id).label('times_bought_together')
        ).select_from(OrderItems).join(
            Orders, Orders.order_id == OrderItems.order_id
        ).join(
            ProductVariants, ProductVariants.product_variant_id == OrderItems.product_variant_id
        ).join(
            Products, Products.product_id == ProductVariants.product_id
        ).filter(
            Orders.order_id.in_(
                # Subquery: órdenes que contienen el producto actual
                db.query(OrderItems.order_id).join(
                    ProductVariants, ProductVariants.product_variant_id == OrderItems.product_variant_id
                ).filter(
                    ProductVariants.product_id == product_id
                )
            ),
            ProductVariants.product_id != product_id,  # Excluir el producto actual
            Products.is_active == True
        ).group_by(
            ProductVariants.product_id,
            Products.product_name,
            Products.category
        ).order_by(
            func.count(Orders.order_id).desc()
        ).limit(limit).all()

        recommendations = []
        for prod_id, prod_name, prod_category, times_bought in cross_sell_query:
            recommendations.append({
                'product_id': prod_id,
                'product_name': prod_name,
                'category': prod_category,
                'times_bought_together': times_bought,
                'recommendation_type': 'cross_sell'
            })

        logger.info(f"💡 {len(recommendations)} recomendaciones de cross-sell encontradas para {product_id}")

        return recommendations
