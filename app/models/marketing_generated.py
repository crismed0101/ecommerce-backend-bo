from typing import Optional
import datetime
import decimal

from sqlalchemy import Boolean, CheckConstraint, Computed, Date, DateTime, Enum, ForeignKeyConstraint, Index, Integer, Numeric, PrimaryKeyConstraint, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.core.database import Base

class AdAccounts(Base):
    __tablename__ = 'ad_accounts'
    __table_args__ = (
        PrimaryKeyConstraint('ad_account_id', name='ad_accounts_pkey'),
        UniqueConstraint('account_external_id', name='unique_account_external_id'),
        Index('idx_ad_accounts_active', 'is_active'),
        Index('idx_ad_accounts_platform', 'platform'),
        {'comment': 'Cuentas de publicidad (principalmente Facebook Ads). Agrupa '
                'métricas diarias.',
     'schema': 'marketing'}
    )

    ad_account_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    ad_account_name: Mapped[str] = mapped_column(String(200), nullable=False)
    platform: Mapped[str] = mapped_column(Enum('facebook', 'instagram', 'google', 'tiktok', 'pinterest', name='ad_platform', schema='marketing'), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('true'))
    account_external_id: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

    ad_daily_metrics_old: Mapped[list['AdDailyMetricsOld']] = relationship('AdDailyMetricsOld', back_populates='ad_account')


class Campaigns(Base):
    __tablename__ = 'campaigns'
    __table_args__ = (
        CheckConstraint("status::text = ANY (ARRAY['active'::character varying, 'paused'::character varying, 'archived'::character varying]::text[])", name='check_campaign_status'),
        PrimaryKeyConstraint('campaign_id', name='campaigns_pkey'),
        UniqueConstraint('campaign_external_id', name='campaigns_campaign_external_id_key'),
        Index('idx_campaigns_active', 'is_active'),
        Index('idx_campaigns_external', 'campaign_external_id'),
        {'schema': 'marketing'}
    )

    campaign_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    campaign_external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    campaign_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'active'::character varying"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('true'))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    campaign_objective: Mapped[Optional[str]] = mapped_column(String(50))

    ad_sets: Mapped[list['AdSets']] = relationship('AdSets', back_populates='campaign')


class AdDailyMetricsOld(Base):
    __tablename__ = 'ad_daily_metrics_old'
    __table_args__ = (
        CheckConstraint('amount_spent >= 0::numeric AND impressions >= 0 AND clicks >= 0 AND conversions >= 0', name='check_metrics_not_negative'),
        ForeignKeyConstraint(['ad_account_id'], ['marketing.ad_accounts.ad_account_id'], ondelete='CASCADE', name='ad_daily_metrics_ad_account_id_fkey'),
        PrimaryKeyConstraint('metric_id', name='ad_daily_metrics_pkey'),
        UniqueConstraint('ad_account_id', 'metric_date', name='unique_account_date'),
        Index('idx_ad_metrics_account', 'ad_account_id'),
        Index('idx_ad_metrics_date', 'metric_date'),
        {'comment': 'Métricas diarias de Facebook Ads. Al insertar/actualizar '
                'amount_spent > 0, se crea\n'
                'automáticamente una transacción financiera tipo EXPENSE desde '
                'cuenta ACC-WALLBIT en USDT.',
     'schema': 'marketing'}
    )

    metric_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    ad_account_id: Mapped[str] = mapped_column(String(20), nullable=False)
    metric_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    amount_spent: Mapped[decimal.Decimal] = mapped_column(Numeric(10, 2), nullable=False, server_default=text('0'))
    currency: Mapped[str] = mapped_column(Enum('BOB', 'USD', 'USDT', 'USDC', 'EUR', 'CNY', 'PEN', 'ARS', 'COP', 'PYG', 'BRL', name='currency_code', schema='finance'), nullable=False)
    impressions: Mapped[Optional[int]] = mapped_column(Integer, server_default=text('0'))
    clicks: Mapped[Optional[int]] = mapped_column(Integer, server_default=text('0'))
    conversions: Mapped[Optional[int]] = mapped_column(Integer, server_default=text('0'))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

    ad_account: Mapped['AdAccounts'] = relationship('AdAccounts', back_populates='ad_daily_metrics_old')


class AdSets(Base):
    __tablename__ = 'ad_sets'
    __table_args__ = (
        CheckConstraint("status::text = ANY (ARRAY['active'::character varying, 'paused'::character varying, 'archived'::character varying]::text[])", name='check_adset_status'),
        CheckConstraint('targeting_age_min IS NULL OR targeting_age_min >= 13 AND targeting_age_min <= 65', name='check_adset_age'),
        ForeignKeyConstraint(['campaign_id'], ['marketing.campaigns.campaign_id'], ondelete='CASCADE', name='fk_adset_campaign'),
        PrimaryKeyConstraint('ad_set_id', name='ad_sets_pkey'),
        UniqueConstraint('ad_set_external_id', name='ad_sets_ad_set_external_id_key'),
        Index('idx_adsets_active', 'is_active'),
        Index('idx_adsets_campaign', 'campaign_id'),
        Index('idx_adsets_external', 'ad_set_external_id'),
        {'schema': 'marketing'}
    )

    ad_set_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    campaign_id: Mapped[str] = mapped_column(String(20), nullable=False)
    ad_set_external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    ad_set_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'active'::character varying"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('true'))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    targeting_age_min: Mapped[Optional[int]] = mapped_column(Integer)
    targeting_age_max: Mapped[Optional[int]] = mapped_column(Integer)
    targeting_gender: Mapped[Optional[str]] = mapped_column(Enum('male', 'female', 'all', name='gender_targeting', schema='marketing'))
    targeting_locations: Mapped[Optional[dict]] = mapped_column(JSONB)

    campaign: Mapped['Campaigns'] = relationship('Campaigns', back_populates='ad_sets')
    ads: Mapped[list['Ads']] = relationship('Ads', back_populates='ad_set')


class Ads(Base):
    __tablename__ = 'ads'
    __table_args__ = (
        ForeignKeyConstraint(['ad_set_id'], ['marketing.ad_sets.ad_set_id'], ondelete='CASCADE', name='fk_ad_adset'),
        PrimaryKeyConstraint('ad_id', name='ads_pkey'),
        UniqueConstraint('ad_external_id', name='ads_ad_external_id_key'),
        Index('idx_ads_adset', 'ad_set_id'),
        Index('idx_ads_creative_type', 'creative_type'),
        Index('idx_ads_external', 'ad_external_id'),
        Index('idx_ads_status', 'status'),
        {'schema': 'marketing'}
    )

    ad_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    ad_set_id: Mapped[str] = mapped_column(String(20), nullable=False)
    ad_external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    ad_name: Mapped[str] = mapped_column(String(255), nullable=False)
    creative_type: Mapped[str] = mapped_column(Enum('image', 'video', 'carousel', 'collection', 'slideshow', name='creative_type', schema='marketing'), nullable=False)
    status: Mapped[str] = mapped_column(Enum('active', 'paused', 'archived', name='ad_status', schema='marketing'), nullable=False, server_default=text("'active'::marketing.ad_status"))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP'))

    ad_set: Mapped['AdSets'] = relationship('AdSets', back_populates='ads')
    ad_creative_versions: Mapped[list['AdCreativeVersions']] = relationship('AdCreativeVersions', back_populates='ad')
    ad_daily_metrics: Mapped[list['AdDailyMetrics']] = relationship('AdDailyMetrics', back_populates='ad')
    ad_daily_metrics_breakdown: Mapped[list['AdDailyMetricsBreakdown']] = relationship('AdDailyMetricsBreakdown', back_populates='ad')


class AdCreativeVersions(Base):
    __tablename__ = 'ad_creative_versions'
    __table_args__ = (
        CheckConstraint('valid_to IS NULL OR valid_to >= valid_from', name='check_version_dates'),
        ForeignKeyConstraint(['ad_id'], ['marketing.ads.ad_id'], ondelete='CASCADE', name='fk_version_ad'),
        PrimaryKeyConstraint('version_id', name='ad_creative_versions_pkey'),
        UniqueConstraint('ad_id', 'version_number', name='unique_ad_version_number'),
        Index('idx_versions_ad', 'ad_id'),
        Index('idx_versions_current', 'ad_id'),
        Index('idx_versions_valid', 'ad_id', 'valid_from', 'valid_to'),
        {'schema': 'marketing'}
    )

    version_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    ad_id: Mapped[str] = mapped_column(String(20), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    valid_from: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    creative_url: Mapped[Optional[str]] = mapped_column(Text)
    ad_copy: Mapped[Optional[str]] = mapped_column(Text)
    call_to_action: Mapped[Optional[str]] = mapped_column(String(50))
    destination_url: Mapped[Optional[str]] = mapped_column(Text)
    valid_to: Mapped[Optional[datetime.date]] = mapped_column(Date)

    ad: Mapped['Ads'] = relationship('Ads', back_populates='ad_creative_versions')


class AdDailyMetrics(Base):
    __tablename__ = 'ad_daily_metrics'
    __table_args__ = (
        CheckConstraint('amount_spent >= 0::numeric', name='check_amount_spent'),
        CheckConstraint('clicks >= 0', name='check_clicks'),
        CheckConstraint('impressions >= 0', name='check_impressions'),
        ForeignKeyConstraint(['ad_id'], ['marketing.ads.ad_id'], ondelete='CASCADE', name='fk_metric_ad'),
        PrimaryKeyConstraint('metric_id', name='ad_daily_metrics_pkey1'),
        UniqueConstraint('ad_id', 'metric_date', name='unique_ad_metric_date'),
        Index('idx_metrics_ad', 'ad_id'),
        Index('idx_metrics_ad_date', 'ad_id', 'metric_date'),
        Index('idx_metrics_date', 'metric_date'),
        {'schema': 'marketing'}
    )

    metric_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    ad_id: Mapped[str] = mapped_column(String(20), nullable=False)
    metric_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    amount_spent: Mapped[decimal.Decimal] = mapped_column(Numeric(10, 2), nullable=False, server_default=text('0'))
    currency: Mapped[str] = mapped_column(Enum('BOB', 'USD', 'USDT', 'USDC', 'EUR', 'CNY', 'PEN', 'ARS', 'COP', 'PYG', 'BRL', name='currency_code', schema='finance'), nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    conversions_facebook: Mapped[Optional[int]] = mapped_column(Integer, server_default=text('0'))
    reach: Mapped[Optional[int]] = mapped_column(Integer, server_default=text('0'))
    frequency: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(5, 2), server_default=text('0'))
    video_views: Mapped[Optional[int]] = mapped_column(Integer, server_default=text('0'))
    video_thruplay: Mapped[Optional[int]] = mapped_column(Integer, server_default=text('0'))
    video_avg_watch_time: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(5, 2), server_default=text('0'))
    ctr: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(5, 2), Computed('\nCASE\n    WHEN (impressions > 0) THEN round((((clicks)::numeric / (impressions)::numeric) * (100)::numeric), 2)\n    ELSE (0)::numeric\nEND', persisted=True))
    cpc: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(10, 2), Computed('\nCASE\n    WHEN (clicks > 0) THEN round((amount_spent / (clicks)::numeric), 2)\n    ELSE (0)::numeric\nEND', persisted=True))
    cpm: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(10, 2), Computed('\nCASE\n    WHEN (impressions > 0) THEN round(((amount_spent / (impressions)::numeric) * (1000)::numeric), 2)\n    ELSE (0)::numeric\nEND', persisted=True))
    completion_rate: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(5, 2), Computed('\nCASE\n    WHEN (video_views > 0) THEN round((((video_thruplay)::numeric / (video_views)::numeric) * (100)::numeric), 2)\n    ELSE (0)::numeric\nEND', persisted=True))

    ad: Mapped['Ads'] = relationship('Ads', back_populates='ad_daily_metrics')


class AdDailyMetricsBreakdown(Base):
    __tablename__ = 'ad_daily_metrics_breakdown'
    __table_args__ = (
        CheckConstraint('amount_spent >= 0::numeric', name='check_breakdown_spent'),
        CheckConstraint('clicks >= 0', name='check_breakdown_clicks'),
        CheckConstraint('impressions >= 0', name='check_breakdown_impressions'),
        ForeignKeyConstraint(['ad_id'], ['marketing.ads.ad_id'], ondelete='CASCADE', name='fk_breakdown_ad'),
        PrimaryKeyConstraint('breakdown_id', name='ad_daily_metrics_breakdown_pkey'),
        UniqueConstraint('ad_id', 'metric_date', 'breakdown_type', 'breakdown_value', name='unique_ad_breakdown'),
        Index('idx_breakdown_ad', 'ad_id'),
        Index('idx_breakdown_lookup', 'ad_id', 'metric_date', 'breakdown_type'),
        Index('idx_breakdown_type', 'breakdown_type'),
        Index('idx_breakdown_value', 'breakdown_type', 'breakdown_value'),
        {'schema': 'marketing'}
    )

    breakdown_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    ad_id: Mapped[str] = mapped_column(String(20), nullable=False)
    metric_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    breakdown_type: Mapped[str] = mapped_column(Enum('placement', 'age', 'gender', 'region', 'device', 'hour', name='breakdown_type', schema='marketing'), nullable=False)
    breakdown_value: Mapped[str] = mapped_column(String(100), nullable=False)
    amount_spent: Mapped[decimal.Decimal] = mapped_column(Numeric(10, 2), nullable=False, server_default=text('0'))
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    conversions_facebook: Mapped[Optional[int]] = mapped_column(Integer, server_default=text('0'))
    ctr: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(5, 2), Computed('\nCASE\n    WHEN (impressions > 0) THEN round((((clicks)::numeric / (impressions)::numeric) * (100)::numeric), 2)\n    ELSE (0)::numeric\nEND', persisted=True))
    cpc: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(10, 2), Computed('\nCASE\n    WHEN (clicks > 0) THEN round((amount_spent / (clicks)::numeric), 2)\n    ELSE (0)::numeric\nEND', persisted=True))
    cpm: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(10, 2), Computed('\nCASE\n    WHEN (impressions > 0) THEN round(((amount_spent / (impressions)::numeric) * (1000)::numeric), 2)\n    ELSE (0)::numeric\nEND', persisted=True))

    ad: Mapped['Ads'] = relationship('Ads', back_populates='ad_daily_metrics_breakdown')
