"""
Dynamic Query Template Generator

Generates SQL templates dynamically based on actual data schema.
Uses ColumnResolver to map semantic terms to actual column names.
"""

from typing import Dict, List, Optional
from loguru import logger
import pandas as pd

from .column_resolver import ColumnResolver
from .query_templates import QueryTemplate


class TemplateGenerator:
    """Generates query templates dynamically based on actual schema."""
    
    def __init__(self, schema_columns: List[str]):
        """
        Initialize template generator.
        
        Args:
            schema_columns: List of actual column names from data
        """
        self.schema_columns = schema_columns
        self.resolver = ColumnResolver(schema_columns)
        self._template_cache: Dict[str, QueryTemplate] = {}
        
    def _resolve(self, term: str) -> Optional[str]:
        """Resolve a semantic term to actual column name."""
        col = self.resolver.resolve(term)
        if col:
            # Quote column names with spaces or special chars
            if ' ' in col or '-' in col:
                return f'"{col}"'
            return col
        return None
    
    def _safe_resolve(self, term: str, fallback: str = None) -> str:
        """Resolve with fallback to prevent template failures."""
        col = self._resolve(term)
        if col:
            return col
        if fallback:
            logger.warning(f"Could not resolve '{term}', using fallback: {fallback}")
            return fallback
        logger.warning(f"Could not resolve '{term}', skipping")
        return f"NULL AS {term}"
    
    def generate_funnel_analysis(self) -> Optional[QueryTemplate]:
        """Generate funnel analysis template."""
        funnel_col = self._resolve('funnel')
        spend_col = self._resolve('spend')
        impressions_col = self._resolve('impressions')
        clicks_col = self._resolve('clicks')
        conversions_col = self._resolve('conversions')
        
        if not all([funnel_col, spend_col, clicks_col, conversions_col]):
            logger.warning("Missing required columns for funnel analysis")
            return None
            
        sql = f"""
WITH stage_totals AS (
    SELECT
        {funnel_col} AS funnel_stage,
        SUM({spend_col}) AS stage_spend,
        SUM({impressions_col or 'NULL'}) AS stage_impressions,
        SUM({clicks_col}) AS stage_clicks,
        SUM({conversions_col}) AS stage_conversions
    FROM all_campaigns
    WHERE {funnel_col} IS NOT NULL AND {funnel_col} != 'Unknown'
    GROUP BY {funnel_col}
)
SELECT
    funnel_stage,
    stage_spend,
    stage_impressions,
    stage_clicks,
    stage_conversions,
    ROUND((stage_clicks / NULLIF(stage_impressions, 0)) * 100, 2) AS ctr,
    ROUND(stage_spend / NULLIF(stage_clicks, 0), 2) AS cpc,
    ROUND(stage_spend / NULLIF(stage_conversions, 0), 2) AS cpa,
    ROUND((stage_conversions / NULLIF(stage_clicks, 0)) * 100, 2) AS conversion_rate
FROM stage_totals
ORDER BY 
    CASE funnel_stage
        WHEN 'Awareness' THEN 1
        WHEN 'Consideration' THEN 2
        WHEN 'Conversion' THEN 3
        ELSE 4
    END
        """  # nosec B608
        
        return QueryTemplate(
            name="Marketing Funnel Analysis",
            patterns=["funnel", "conversion funnel", "drop off", "drop-off", "funnel analysis", "marketing funnel", "awareness", "consideration", "funnel performance", "funnel stages"],
            sql=sql,
            description="Marketing funnel by stage (Awareness → Consideration → Conversion) with performance metrics"
        )
    
    def generate_roas_analysis(self) -> Optional[QueryTemplate]:
        """Generate ROAS analysis template."""
        campaign_col = self._resolve('campaign')
        spend_col = self._resolve('spend')
        revenue_col = self._resolve('revenue') or self._resolve('conversion_value')
        
        if not all([campaign_col, spend_col, revenue_col]):
            return None
            
        sql = f"""
SELECT
    {campaign_col} AS campaign_name,
    SUM({spend_col}) AS total_spend,
    SUM({revenue_col}) AS total_revenue,
    ROUND(SUM({revenue_col}) / NULLIF(SUM({spend_col}), 0), 2) AS roas,
    ROUND(SUM({revenue_col}) - SUM({spend_col}), 2) AS net_revenue
FROM all_campaigns
GROUP BY {campaign_col}
HAVING total_spend > 0
ORDER BY roas DESC
        """  # nosec B608
        
        return QueryTemplate(
            name="ROAS Performance Analysis",
            patterns=["roas", "return on ad spend", "roi", "return on investment", "profitable", "profitability"],
            sql=sql,
            description="Campaign ROAS and net revenue analysis"
        )

    def generate_growth_analysis(self) -> Optional[QueryTemplate]:
        """Generate growth and trend analysis template."""
        date_col = self._resolve('date')
        spend_col = self._resolve('spend')
        conversions_col = self._resolve('conversions')
        
        if not all([date_col, spend_col, conversions_col]):
            return None
            
        sql = f"""
SELECT
    DATE_TRUNC('week', CAST({date_col} AS DATE)) AS week,
    SUM({spend_col}) AS weekly_spend,
    SUM({conversions_col}) AS weekly_conversions,
    LAG(SUM({conversions_col})) OVER (ORDER BY week) AS prev_week_conversions,
    ROUND((SUM({conversions_col}) - LAG(SUM({conversions_col})) OVER (ORDER BY week)) / NULLIF(LAG(SUM({conversions_col})) OVER (ORDER BY week), 0) * 100, 2) AS growth_percentage
FROM all_campaigns
GROUP BY week
ORDER BY week
        """  # nosec B608
        
        return QueryTemplate(
            name="Weekly Growth Analysis",
            patterns=["growth", "trend", "wow", "week over week", "over time", "changes", "increase", "decrease"],
            sql=sql,
            description="Week-over-week conversion growth and spend trends"
        )
    
    def generate_monthly_performance(self) -> Optional[QueryTemplate]:
        """Generate monthly performance template."""
        date_col = self._resolve('date')
        spend_col = self._resolve('spend')
        impressions_col = self._resolve('impressions')
        clicks_col = self._resolve('clicks')
        conversions_col = self._resolve('conversions')
        
        if not all([date_col, spend_col]):
            return None
            
        sql = f"""
SELECT
    DATE_TRUNC('month', CAST({date_col} AS DATE)) AS month_date,
    STRFTIME(DATE_TRUNC('month', CAST({date_col} AS DATE)), '%b-%Y') AS month_label,
    SUM({spend_col}) AS total_spend,
    SUM({impressions_col or '0'}) AS total_impressions,
    SUM({clicks_col or '0'}) AS total_clicks,
    SUM({conversions_col or '0'}) AS total_conversions,
    ROUND((SUM({clicks_col or '0'}) / NULLIF(SUM({impressions_col or '1'}), 0)) * 100, 2) AS ctr,
    ROUND(SUM({spend_col}) / NULLIF(SUM({clicks_col or '1'}), 0), 2) AS cpc,
    ROUND(SUM({spend_col}) / NULLIF(SUM({conversions_col or '1'}), 0), 2) AS cpa,
    ROUND((SUM({conversions_col or '0'}) / NULLIF(SUM({clicks_col or '1'}), 0)) * 100, 2) AS conversion_rate
FROM all_campaigns
GROUP BY month_date, month_label
ORDER BY month_date
        """  # nosec B608
        
        return QueryTemplate(
            name="Monthly Performance Analysis",
            patterns=["monthly", "by month", "month over month", "mom", "monthly performance", "monthly trends", "month by month"],
            sql=sql,
            description="Monthly aggregation of key performance metrics"
        )
    
    def generate_top_campaigns(self) -> Optional[QueryTemplate]:
        """Generate top campaigns template."""
        campaign_col = self._resolve('campaign')
        platform_col = self._resolve('platform')
        channel_col = self._resolve('channel')
        spend_col = self._resolve('spend')
        conversions_col = self._resolve('conversions')
        
        if not all([campaign_col, spend_col, conversions_col]):
            return None
            
        # Build GROUP BY clause
        group_cols = [campaign_col]
        select_cols = [f"{campaign_col} AS campaign_name"]
        
        if platform_col:
            group_cols.append(platform_col)
            select_cols.append(f"{platform_col} AS platform")
        if channel_col:
            group_cols.append(channel_col)
            select_cols.append(f"{channel_col} AS channel")
            
        sql = f"""
SELECT
    {', '.join(select_cols)},
    SUM({spend_col}) AS total_spend,
    SUM({conversions_col}) AS total_conversions,
    ROUND(SUM({spend_col}) / NULLIF(SUM({conversions_col}), 0), 2) AS cpa
FROM all_campaigns
WHERE {conversions_col} > 0
GROUP BY {', '.join(group_cols)}
ORDER BY total_conversions DESC
LIMIT 10
        """  # nosec B608
        
        return QueryTemplate(
            name="Top Performing Campaigns",
            patterns=["top campaigns", "best campaigns", "top performing", "best performing", "winners", "top 10", "most conversions"],
            sql=sql,
            description="Top 10 campaigns by conversions"
        )
    
    def generate_channel_comparison(self) -> Optional[QueryTemplate]:
        """Generate channel comparison template."""
        channel_col = self._resolve('channel')
        campaign_col = self._resolve('campaign')
        spend_col = self._resolve('spend')
        impressions_col = self._resolve('impressions')
        clicks_col = self._resolve('clicks')
        conversions_col = self._resolve('conversions')
        revenue_col = self._resolve('revenue') or self._resolve('conversion_value')
        
        if not all([channel_col, spend_col]):
            return None
            
        sql = f"""
SELECT
    {channel_col} AS channel,
    COUNT(DISTINCT {campaign_col or '1'}) AS campaign_count,
    SUM({spend_col}) AS total_spend,
    SUM({impressions_col or '0'}) AS total_impressions,
    SUM({clicks_col or '0'}) AS total_clicks,
    SUM({conversions_col or '0'}) AS total_conversions,
    ROUND((SUM({clicks_col or '0'}) / NULLIF(SUM({impressions_col or '1'}), 0)) * 100, 2) AS ctr,
    ROUND(SUM({spend_col}) / NULLIF(SUM({clicks_col or '1'}), 0), 2) AS cpc,
    ROUND(SUM({spend_col}) / NULLIF(SUM({conversions_col or '1'}), 0), 2) AS cpa,
    ROUND(SUM({revenue_col or '0'}) / NULLIF(SUM({spend_col}), 0), 2) AS roas
FROM all_campaigns
GROUP BY {channel_col}
ORDER BY total_spend DESC
        """  # nosec B608
        
        return QueryTemplate(
            name="Channel Performance Comparison",
            patterns=["channel comparison", "compare channels", "channel performance", "which channel"],
            sql=sql,
            description="Compare performance metrics across all channels"
        )
    
    def generate_platform_comparison(self) -> Optional[QueryTemplate]:
        """Generate platform comparison template."""
        platform_col = self._resolve('platform')
        campaign_col = self._resolve('campaign')
        spend_col = self._resolve('spend')
        impressions_col = self._resolve('impressions')
        clicks_col = self._resolve('clicks')
        conversions_col = self._resolve('conversions')
        revenue_col = self._resolve('revenue') or self._resolve('conversion_value')
        
        if not all([platform_col, spend_col]):
            return None
            
        sql = f"""
SELECT
    {platform_col} AS platform,
    COUNT(DISTINCT {campaign_col or '1'}) AS campaign_count,
    SUM({spend_col}) AS total_spend,
    SUM({impressions_col or '0'}) AS total_impressions,
    SUM({clicks_col or '0'}) AS total_clicks,
    SUM({conversions_col or '0'}) AS total_conversions,
    ROUND((SUM({clicks_col or '0'}) / NULLIF(SUM({impressions_col or '1'}), 0)) * 100, 2) AS ctr,
    ROUND(SUM({spend_col}) / NULLIF(SUM({clicks_col or '1'}), 0), 2) AS cpc,
    ROUND(SUM({spend_col}) / NULLIF(SUM({conversions_col or '1'}), 0), 2) AS cpa,
    ROUND(SUM({revenue_col or '0'}) / NULLIF(SUM({spend_col}), 0), 2) AS roas
FROM all_campaigns
GROUP BY {platform_col}
ORDER BY roas DESC, total_spend DESC
        """  # nosec B608
        
        return QueryTemplate(
            name="Platform Performance Comparison",
            patterns=["platform comparison", "compare platforms", "platform performance", "which platform"],
            sql=sql,
            description="Compare performance metrics across all platforms"
        )
    
    def generate_summary(self) -> Optional[QueryTemplate]:
        """Generate overall summary template."""
        campaign_col = self._resolve('campaign')
        platform_col = self._resolve('platform')
        channel_col = self._resolve('channel')
        spend_col = self._resolve('spend')
        impressions_col = self._resolve('impressions')
        clicks_col = self._resolve('clicks')
        conversions_col = self._resolve('conversions')
        
        if not spend_col:
            return None
            
        sql = f"""
SELECT
    COUNT(DISTINCT {campaign_col or '1'}) AS total_campaigns,
    COUNT(DISTINCT {platform_col or '1'}) AS total_platforms,
    COUNT(DISTINCT {channel_col or '1'}) AS total_channels,
    SUM({spend_col}) AS total_spend,
    SUM({impressions_col or '0'}) AS total_impressions,
    SUM({clicks_col or '0'}) AS total_clicks,
    SUM({conversions_col or '0'}) AS total_conversions,
    ROUND((SUM({clicks_col or '0'}) / NULLIF(SUM({impressions_col or '1'}), 0)) * 100, 2) AS overall_ctr,
    ROUND(SUM({spend_col}) / NULLIF(SUM({clicks_col or '1'}), 0), 2) AS overall_cpc,
    ROUND(SUM({spend_col}) / NULLIF(SUM({conversions_col or '1'}), 0), 2) AS overall_cpa
FROM all_campaigns
        """  # nosec B608
        
        return QueryTemplate(
            name="Overall Summary",
            patterns=["summary", "overview", "overall", "total", "all metrics", "show all"],
            sql=sql,
            description="High-level summary of all campaign performance"
        )
    
    def generate_device_performance(self) -> Optional[QueryTemplate]:
        """Generate device performance template for mobile vs desktop analysis."""
        device_col = self._resolve('device') or self._resolve('device_type')
        campaign_col = self._resolve('campaign')
        spend_col = self._resolve('spend')
        impressions_col = self._resolve('impressions')
        clicks_col = self._resolve('clicks')
        conversions_col = self._resolve('conversions')
        
        if not all([device_col, spend_col]):
            logger.warning("Missing required columns for device performance analysis")
            return None
            
        sql = f"""
SELECT
    {device_col} AS device_type,
    COUNT(DISTINCT {campaign_col or '1'}) AS campaign_count,
    SUM({spend_col}) AS total_spend,
    SUM({impressions_col or '0'}) AS total_impressions,
    SUM({clicks_col or '0'}) AS total_clicks,
    SUM({conversions_col or '0'}) AS total_conversions,
    ROUND((SUM({clicks_col or '0'}) / NULLIF(SUM({impressions_col or '1'}), 0)) * 100, 2) AS ctr,
    ROUND(SUM({spend_col}) / NULLIF(SUM({clicks_col or '1'}), 0), 2) AS cpc,
    ROUND(SUM({spend_col}) / NULLIF(SUM({conversions_col or '1'}), 0), 2) AS cpa,
    ROUND((SUM({conversions_col or '0'}) / NULLIF(SUM({clicks_col or '1'}), 0)) * 100, 2) AS conversion_rate
FROM all_campaigns
WHERE {device_col} IS NOT NULL AND {device_col} != 'Unknown'
GROUP BY {device_col}
ORDER BY total_spend DESC
        """  # nosec B608
        
        return QueryTemplate(
            name="Device Performance Analysis",
            patterns=[
                "device performance", "mobile vs desktop", "mobile versus desktop", 
                "device type", "mobile and desktop", "desktop and mobile", 
                "mobile or desktop", "device comparison", "mobile desktop",
                "compare device", "by device", "mobile performance", "desktop performance",
                "is mobile", "is desktop", "how is mobile", "how is desktop"
            ],
            sql=sql,
            description="Performance breakdown by device type (Mobile, Desktop, Tablet)"
        )
    
    def generate_all_templates(self) -> Dict[str, QueryTemplate]:
        """Generate all available templates based on schema."""
        templates = {}
        
        generators = [
            ("funnel_analysis", self.generate_funnel_analysis),
            ("device_performance", self.generate_device_performance),  # Added for mobile vs desktop
            ("top_campaigns", self.generate_top_campaigns),
            ("channel_comparison", self.generate_channel_comparison),
            ("platform_comparison", self.generate_platform_comparison),
            ("roas_analysis", self.generate_roas_analysis),
            ("growth_analysis", self.generate_growth_analysis),
            ("monthly_performance", self.generate_monthly_performance),
            ("summary", self.generate_summary),
        ]
        
        for name, generator in generators:
            try:
                template = generator()
                if template:
                    templates[name] = template
                    logger.debug(f"Generated template: {name}")
                else:
                    logger.warning(f"Could not generate template: {name} (missing columns)")
            except Exception as e:
                logger.error(f"Error generating template {name}: {e}")
                
        logger.info(f"Generated {len(templates)} templates from schema")
        return templates


def load_schema_from_parquet(parquet_path: str) -> List[str]:
    """Load column names from Parquet file."""
    try:
        df = pd.read_parquet(parquet_path)
        return list(df.columns)
    except Exception as e:
        logger.error(f"Failed to load schema from {parquet_path}: {e}")
        return []


def generate_templates_for_schema(schema_columns: List[str]) -> Dict[str, QueryTemplate]:
    """
    Generate query templates for a given schema.
    
    Args:
        schema_columns: List of actual column names
        
    Returns:
        Dictionary of template name -> QueryTemplate
    """
    generator = TemplateGenerator(schema_columns)
    return generator.generate_all_templates()
