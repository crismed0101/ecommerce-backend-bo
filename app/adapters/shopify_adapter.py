"""
ShopifyAdapter - Transforma webhooks de Shopify a nuestro formato

Responsabilidad ÚNICA:
- Conocer el formato de Shopify
- Transformar a OrderCreate (nuestro formato)
- NO conoce lógica de negocio
"""

from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class ShopifyAdapter:
    """
    Adapter para Shopify

    Transforma datos de webhook de Shopify al formato interno
    """

    @staticmethod
    def transform_order(shopify_webhook: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transformar orden de Shopify a nuestro formato

        Args:
            shopify_webhook: Webhook completo de Shopify

        Returns:
            Dict compatible con OrderCreate schema
        """
        logger.info(f"Transforming Shopify order: {shopify_webhook.get('id')}")

        # Extraer note_attributes (aquí están nombre, teléfono, UTM, etc.)
        note_attrs = ShopifyAdapter._extract_note_attributes(shopify_webhook)

        # Extraer datos de customer
        customer_data = ShopifyAdapter._extract_customer(shopify_webhook, note_attrs)

        # Extraer items (productos reales, sin "Entrega prioritaria")
        items_data = ShopifyAdapter._extract_items(shopify_webhook)

        # Detectar envío prioritario
        priority_shipping = ShopifyAdapter._extract_priority_shipping(shopify_webhook)

        # Extraer UTM parameters
        utm_data = ShopifyAdapter._extract_utm(note_attrs)

        # Construir objeto OrderCreate
        order_data = {
            "customer": customer_data,
            "items": items_data,
            "is_priority_shipping": priority_shipping['is_priority'],
            "priority_shipping_cost": priority_shipping['cost'],
            "utm_source": utm_data.get('utm_source'),
            "utm_medium": utm_data.get('utm_medium'),
            "utm_campaign": utm_data.get('utm_campaign'),
            "utm_content": utm_data.get('utm_content'),
            "utm_term": utm_data.get('utm_term'),
            "external_order_id": str(shopify_webhook.get('id')),
            "total": float(shopify_webhook.get('current_total_price', 0)),
            "currency": shopify_webhook.get('currency', 'BOB')
        }

        logger.info(f"✅ Shopify order transformed: {len(items_data)} items, "
                   f"priority_shipping={priority_shipping['is_priority']}")

        return order_data

    @staticmethod
    def _extract_note_attributes(webhook: Dict) -> Dict[str, str]:
        """
        Extraer note_attributes a diccionario

        Shopify envía:
        [
          {"name": "Nombre Completo", "value": "ELIAS"},
          {"name": "Celular con Whatsapp", "value": "75538090"}
        ]

        Retorna:
        {
          "Nombre Completo": "ELIAS",
          "Celular con Whatsapp": "75538090"
        }
        """
        note_attrs = webhook.get('note_attributes', [])
        return {attr['name']: attr['value'] for attr in note_attrs if attr.get('value')}

    @staticmethod
    def _extract_customer(webhook: Dict, note_attrs: Dict) -> Dict[str, Any]:
        """
        Extraer datos del customer

        Shopify tiene customer object, pero los datos reales están en note_attributes
        """
        # Mapear ciudad a department
        ciudad = note_attrs.get('Ciudad', '').upper()
        department_map = {
            'LA PAZ': 'LA_PAZ',
            'LAPAZ': 'LA_PAZ',
            'COCHABAMBA': 'COCHABAMBA',
            'SANTA CRUZ': 'SANTA_CRUZ',
            'SANTACRUZ': 'SANTA_CRUZ',
            'ORURO': 'ORURO',
            'POTOSI': 'POTOSI',
            'POTOSÍ': 'POTOSI',
            'TARIJA': 'TARIJA',
            'CHUQUISACA': 'CHUQUISACA',
            'BENI': 'BENI',
            'PANDO': 'PANDO'
        }

        department = department_map.get(ciudad, 'LA_PAZ')  # Default LA_PAZ

        return {
            "full_name": note_attrs.get('Nombre Completo', 'Cliente Shopify'),
            "phone": note_attrs.get('Celular con Whatsapp ', '').strip(),  # Nota el espacio al final
            "email": webhook.get('customer', {}).get('email'),
            "department": department,
            "address": note_attrs.get('Dirección Completa', 'Sin dirección'),
            "reference": note_attrs.get('Referencia')
        }

    @staticmethod
    def _extract_items(webhook: Dict) -> List[Dict[str, Any]]:
        """
        Extraer line_items (solo productos reales)

        Filtra items como "Entrega en las próximas 24 horas" (product_id = null)
        """
        line_items = webhook.get('line_items', [])

        items = []
        for item in line_items:
            # Ignorar items sin product_id (envío prioritario, etc.)
            if item.get('product_id') is None:
                logger.debug(f"Skipping non-product item: {item.get('title')}")
                continue

            items.append({
                "shopify_product_id": item.get('product_id'),
                "shopify_variant_id": item.get('variant_id'),
                "product_name": item.get('title'),
                "sku": item.get('sku'),  # Puede ser None
                "quantity": item.get('quantity', 1),
                "unit_price": float(item.get('price', 0))
            })

        return items

    @staticmethod
    def _extract_priority_shipping(webhook: Dict) -> Dict[str, Any]:
        """
        Detectar si tiene envío prioritario

        Busca item con title "Entrega en las próximas 24 horas"
        """
        line_items = webhook.get('line_items', [])

        for item in line_items:
            title = item.get('title', '').lower()
            if 'entrega' in title and '24 horas' in title:
                return {
                    'is_priority': True,
                    'cost': float(item.get('price', 0))
                }

        return {
            'is_priority': False,
            'cost': 0.0
        }

    @staticmethod
    def _extract_utm(note_attrs: Dict) -> Dict[str, str]:
        """
        Extraer UTM parameters

        Usado para tracking de ROAS (qué ad generó esta orden)
        """
        return {
            'utm_source': note_attrs.get('UTM source'),
            'utm_medium': note_attrs.get('UTM medium'),
            'utm_campaign': note_attrs.get('UTM campaign'),
            'utm_content': note_attrs.get('UTM content'),  # ← Este es el ad_external_id
            'utm_term': note_attrs.get('UTM term')
        }
