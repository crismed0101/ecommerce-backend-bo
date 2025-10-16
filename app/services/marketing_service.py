"""
MarketingService - Gestión de campañas publicitarias y métricas

REEMPLAZA TRIGGERS:
- marketing.trg_create_transaction_from_ads
- marketing.trg_02_versions_close_previous
- marketing.trg_01_versions_generate_number
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional, Dict, List
from decimal import Decimal
from datetime import datetime, date
import logging

from app.models import Ads, AdDailyMetrics, AdCreativeVersions, Campaigns
from app.services.id_generator import IDGenerator
from app.services.finance_service import FinanceService

logger = logging.getLogger(__name__)


class MarketingService:
    """Service para gestión de marketing y publicidad"""

    @staticmethod
    def create_ad_with_spend(
        db: Session,
        campaign_id: str,
        ad_account_id: str,
        ad_name: str,
        ad_platform: str,
        ad_content: Optional[str] = None,
        target_audience: Optional[Dict] = None,
        daily_budget: Optional[Decimal] = None,
        payment_account_id: Optional[str] = None,
        initial_spend: Optional[Decimal] = None,
        currency: str = "BOB"
    ):
        """
        Crear ad y registrar gasto inicial

        Args:
            ad_platform: 'facebook', 'google', 'tiktok'
        """
        try:
            ad_id = IDGenerator.generate_ad_id(db)

            ad = Ads(
                ad_id=ad_id,
                campaign_id=campaign_id,
                ad_account_id=ad_account_id,
                ad_name=ad_name,
                ad_platform=ad_platform,
                ad_content=ad_content,
                target_audience=target_audience,
                daily_budget=daily_budget,
                status='active'
            )
            db.add(ad)
            db.flush()

            logger.info(f"Ad creado: {ad_id} ({ad_name} en {ad_platform})")

            if initial_spend and initial_spend > 0 and payment_account_id:
                MarketingService._create_ad_spend_transaction(
                    db=db,
                    ad_id=ad_id,
                    payment_account_id=payment_account_id,
                    amount=initial_spend,
                    currency=currency,
                    description=f"Gasto inicial ad {ad_name}"
                )

            db.commit()
            return ad

        except Exception as e:
            db.rollback()
            logger.error(f"Error creando ad: {str(e)}")
            raise ValueError(f"Error creando ad: {str(e)}")

    @staticmethod
    def _create_ad_spend_transaction(
        db: Session,
        ad_id: str,
        payment_account_id: str,
        amount: Decimal,
        currency: str,
        description: Optional[str] = None
    ):
        """Crear transacción de gasto publicitario usando FinanceService"""
        FinanceService.create_transaction(
            db=db,
            transaction_type='expense',
            from_account_id=payment_account_id,
            to_account_id=None,
            amount=amount,
            currency=currency,
            reference_type='ad_spend',
            reference_id=ad_id,
            description=description or f"Gasto publicitario ad {ad_id}"
        )
        logger.info(f"Transacción de gasto publicitario creada: {amount} {currency} para ad {ad_id}")

    @staticmethod
    def create_ad_version(
        db: Session,
        ad_id: str,
        version_name: str,
        version_content: Dict,
        auto_close_previous: bool = True
    ):
        """Crear nueva versión de ad para A/B testing"""
        try:
            if auto_close_previous:
                MarketingService._close_previous_versions(db, ad_id)

            version_number = MarketingService._generate_version_number(db, ad_id)

            version = AdCreativeVersions(
                ad_id=ad_id,
                version_number=version_number,
                version_name=version_name,
                version_content=version_content,
                is_active=True,
                created_at=datetime.now()
            )
            db.add(version)
            db.flush()

            logger.info(f"Versión {version_number} creada para ad {ad_id} ({version_name})")

            db.commit()
            return version

        except Exception as e:
            db.rollback()
            logger.error(f"Error creando versión: {str(e)}")
            raise ValueError(f"Error creando versión: {str(e)}")

    @staticmethod
    def _close_previous_versions(db: Session, ad_id: str):
        """Cerrar todas las versiones activas de un ad"""
        db.query(AdCreativeVersions).filter(
            AdCreativeVersions.ad_id == ad_id,
            AdCreativeVersions.is_active == True
        ).update({
            'is_active': False,
            'closed_at': datetime.now()
        })
        db.flush()
        logger.info(f"Versiones anteriores cerradas para ad {ad_id}")

    @staticmethod
    def _generate_version_number(db: Session, ad_id: str) -> int:
        """Generar número secuencial de versión"""
        max_version = db.query(
            func.coalesce(func.max(AdCreativeVersions.version_number), 0)
        ).filter(
            AdCreativeVersions.ad_id == ad_id
        ).scalar()

        return int(max_version) + 1

    @staticmethod
    def record_ad_metrics(
        db: Session,
        ad_id: str,
        metrics_date: date,
        impressions: int = 0,
        clicks: int = 0,
        conversions: int = 0,
        spend: Decimal = Decimal('0'),
        revenue: Decimal = Decimal('0'),
        currency: str = "BOB"
    ):
        """Registrar métricas de ad con cálculo automático de CTR, CPC, ROAS"""
        try:
            metric_id = IDGenerator.generate_metric_id(db)

            ctr = (clicks / impressions * 100) if impressions > 0 else 0
            cpc = (spend / clicks) if clicks > 0 else 0
            roas = (revenue / spend) if spend > 0 else 0

            metric = AdDailyMetrics(
                metric_id=metric_id,
                ad_id=ad_id,
                metrics_date=metrics_date,
                impressions=impressions,
                clicks=clicks,
                conversions=conversions,
                spend=spend,
                revenue=revenue,
                ctr=Decimal(str(ctr)),
                cpc=cpc,
                roas=roas,
                currency=currency
            )
            db.add(metric)
            db.flush()

            logger.info(f"Métricas registradas para ad {ad_id}: CTR={ctr:.2f}%, CPC={cpc:.2f}, ROAS={roas:.2f}x")

            db.commit()
            return metric

        except Exception as e:
            db.rollback()
            logger.error(f"Error registrando métricas: {str(e)}")
            raise ValueError(f"Error registrando métricas: {str(e)}")

    @staticmethod
    def get_ad_performance(
        db: Session,
        ad_id: str,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> Dict:
        """Obtener performance agregado de un ad"""
        query = db.query(
            func.sum(AdDailyMetrics.impressions).label('total_impressions'),
            func.sum(AdDailyMetrics.clicks).label('total_clicks'),
            func.sum(AdDailyMetrics.conversions).label('total_conversions'),
            func.sum(AdDailyMetrics.spend).label('total_spend'),
            func.sum(AdDailyMetrics.revenue).label('total_revenue')
        ).filter(
            AdDailyMetrics.ad_id == ad_id
        )

        if date_from:
            query = query.filter(AdDailyMetrics.metrics_date >= date_from)
        if date_to:
            query = query.filter(AdDailyMetrics.metrics_date <= date_to)

        result = query.first()

        total_spend = Decimal(str(result.total_spend or 0))
        total_revenue = Decimal(str(result.total_revenue or 0))
        total_impressions = int(result.total_impressions or 0)
        total_clicks = int(result.total_clicks or 0)

        return {
            'ad_id': ad_id,
            'total_impressions': total_impressions,
            'total_clicks': total_clicks,
            'total_conversions': int(result.total_conversions or 0),
            'total_spend': float(total_spend),
            'total_revenue': float(total_revenue),
            'avg_ctr': float((total_clicks / total_impressions * 100) if total_impressions > 0 else 0),
            'avg_cpc': float((total_spend / total_clicks) if total_clicks > 0 else 0),
            'roas': float((total_revenue / total_spend) if total_spend > 0 else 0)
        }

    @staticmethod
    def get_campaign_roas(
        db: Session,
        campaign_id: str,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> Decimal:
        """Calcular ROAS agregado de una campaña"""
        ads = db.query(Ads).filter(Ads.campaign_id == campaign_id).all()
        ad_ids = [ad.ad_id for ad in ads]

        if not ad_ids:
            return Decimal('0')

        query = db.query(
            func.sum(AdDailyMetrics.spend).label('total_spend'),
            func.sum(AdDailyMetrics.revenue).label('total_revenue')
        ).filter(
            AdDailyMetrics.ad_id.in_(ad_ids)
        )

        if date_from:
            query = query.filter(AdDailyMetrics.metrics_date >= date_from)
        if date_to:
            query = query.filter(AdDailyMetrics.metrics_date <= date_to)

        result = query.first()

        total_spend = Decimal(str(result.total_spend or 0))
        total_revenue = Decimal(str(result.total_revenue or 0))

        roas = (total_revenue / total_spend) if total_spend > 0 else Decimal('0')

        logger.info(f"ROAS campaña {campaign_id}: {roas:.2f}x (revenue={total_revenue}, spend={total_spend})")

        return roas

    @staticmethod
    def get_top_performing_ads(
        db: Session,
        campaign_id: Optional[str] = None,
        metric: str = 'roas',
        limit: int = 10
    ) -> List:
        """Obtener ads con mejor performance"""
        query = db.query(
            AdDailyMetrics.ad_id,
            func.avg(AdDailyMetrics.roas).label('avg_roas'),
            func.avg(AdDailyMetrics.ctr).label('avg_ctr'),
            func.sum(AdDailyMetrics.conversions).label('total_conversions')
        ).join(
            Ads, Ads.ad_id == AdDailyMetrics.ad_id
        )

        if campaign_id:
            query = query.filter(Ads.campaign_id == campaign_id)

        query = query.group_by(AdDailyMetrics.ad_id)

        if metric == 'roas':
            query = query.order_by(func.avg(AdDailyMetrics.roas).desc())
        elif metric == 'ctr':
            query = query.order_by(func.avg(AdDailyMetrics.ctr).desc())
        elif metric == 'conversions':
            query = query.order_by(func.sum(AdDailyMetrics.conversions).desc())

        return query.limit(limit).all()
