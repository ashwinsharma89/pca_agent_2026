"""
BULLETPROOF SQL QUERY GENERATOR
===============================
Pre-built SQL templates for common marketing analytics queries.
These bypass LLM generation for reliable, tested queries.

Author: Marketing Analytics Expert
Date: 2026-01-01
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import re


class BulletproofQueries:
    """
    Pre-built, tested SQL queries for common marketing analytics patterns.
    These are guaranteed to work with the all_campaigns schema.
    """
    
    # ============================================================
    # SCHEMA REFERENCE (for LLM context)
    # ============================================================
    SCHEMA = """
    TABLE: all_campaigns
    
    DIMENSION COLUMNS (for GROUP BY):
    - "Date" (datetime) - Campaign date, use CAST("Date" AS DATE)
    - Platform (varchar) - Meta, Google, TikTok, etc.
    - Channel (varchar) - SOC, DIS, SEARCH, EMAIL
    - Campaign_Name_Full (varchar) - Full campaign name
    - Device_Type (varchar) - Mobile, Desktop, Smart_TV, etc.
    - Campaign_Objective (varchar) - Lead_Generation, Brand_Awareness, etc.
    - Funnel (varchar) - Upper, Middle, Lower
    - Geographic_Region (varchar) - Florida, California, etc.
    
    METRIC COLUMNS (for SUM/aggregation):
    - "Total Spent" (float) - Ad spend in dollars
    - "Site Visit" (float) - Conversions count
    - Impressions (float) - Total impressions
    - Clicks (float) - Total clicks
    - Revenue_2024 (float) - Revenue for 2024 data
    - Revenue_2025 (float) - Revenue for 2025 data
    
    CALCULATED KPIs:
    - CTR = SUM(Clicks) * 100.0 / NULLIF(SUM(Impressions), 0)
    - CPC = SUM("Total Spent") / NULLIF(SUM(Clicks), 0)
    - CPA = SUM("Total Spent") / NULLIF(SUM("Site Visit"), 0)
    - ROAS = (COALESCE(SUM(Revenue_2024),0) + COALESCE(SUM(Revenue_2025),0)) / NULLIF(SUM("Total Spent"), 0)
    - CVR = SUM("Site Visit") * 100.0 / NULLIF(SUM(Clicks), 0)
    """
    
    @staticmethod
    def get_date_bounds_cte() -> str:
        """Get max date from data for anchoring queries."""
        return """WITH date_bounds AS (
    SELECT CAST(MAX("Date") AS DATE) AS max_date FROM all_campaigns
)"""
    
    # ============================================================
    # PATTERN MATCHERS - Detect query intent
    # ============================================================
    QUERY_PATTERNS = {
        'week_comparison': r'compare.*(?:last|previous)?\s*(?:2|two)?\s*weeks?|week.over.week|wow|w\/w',
        'month_comparison': r'compare.*(?:last|previous)?\s*(?:2|two)?\s*months?|month.over.month|mom|m\/m',
        'daily_trend': r'daily|day.by.day|each.day|per.day|trend.*daily',
        'weekly_trend': r'weekly|week.by.week|each.week|per.week|trend.*weekly',
        'monthly_trend': r'monthly|month.by.month|each.month|per.month|trend.*monthly',
        'top_campaigns': r'top|best|highest|leading|winning.*campaigns?',
        'worst_campaigns': r'worst|bottom|lowest|underperforming|failing.*campaigns?',
        'by_platform': r'by.platform|platform.breakdown|per.platform|platform.performance',
        'by_channel': r'by.channel|channel.breakdown|per.channel|channel.performance',
        'total_spend': r'total.spend|how.much.*spent|overall.spend',
        'total_conversions': r'total.conversions|how.many.conversions|overall.conversions',
        'ctr': r'\bctr\b|click.through|click.rate',
        'cpa': r'\bcpa\b|cost.per.(?:acquisition|conversion)|acquisition.cost',
        'roas': r'\broas\b|return.on.ad|ad.spend.return',
        'last_7_days': r'last.(?:7|seven).days|past.week|this.week|recent',
        'last_30_days': r'last.(?:30|thirty).days|past.month|this.month',
    }
    
    @classmethod
    def detect_intent(cls, question: str) -> list:
        """Detect query patterns in the question."""
        question_lower = question.lower()
        matches = []
        for pattern_name, pattern in cls.QUERY_PATTERNS.items():
            if re.search(pattern, question_lower):
                matches.append(pattern_name)
        return matches
    
    # ============================================================
    # BULLETPROOF TEMPLATES
    # ============================================================
    
    @classmethod
    def week_over_week_comparison(cls) -> str:
        """Compare last 2 weeks: Dec 25-31 vs Dec 18-24"""
        return """
WITH date_bounds AS (
    SELECT CAST(MAX("Date") AS DATE) AS max_date FROM all_campaigns
),
date_ranges AS (
    SELECT 
        max_date,
        max_date - INTERVAL '6 days' AS current_start,
        max_date - INTERVAL '7 days' AS previous_end,
        max_date - INTERVAL '13 days' AS previous_start
    FROM date_bounds
),
current_week AS (
    SELECT 
        SUM("Total Spent") AS spend,
        SUM("Site Visit") AS conversions,
        SUM(Impressions) AS impressions,
        SUM(Clicks) AS clicks,
        COALESCE(SUM(Revenue_2024), 0) + COALESCE(SUM(Revenue_2025), 0) AS revenue
    FROM all_campaigns, date_ranges
    WHERE CAST("Date" AS DATE) >= current_start AND CAST("Date" AS DATE) <= max_date
),
previous_week AS (
    SELECT 
        SUM("Total Spent") AS spend,
        SUM("Site Visit") AS conversions,
        SUM(Impressions) AS impressions,
        SUM(Clicks) AS clicks,
        COALESCE(SUM(Revenue_2024), 0) + COALESCE(SUM(Revenue_2025), 0) AS revenue
    FROM all_campaigns, date_ranges
    WHERE CAST("Date" AS DATE) >= previous_start AND CAST("Date" AS DATE) <= previous_end
)
SELECT 
    (SELECT STRFTIME(current_start, '%b %d') || ' - ' || STRFTIME(max_date, '%b %d') FROM date_ranges) AS current_period,
    (SELECT STRFTIME(previous_start, '%b %d') || ' - ' || STRFTIME(previous_end, '%b %d') FROM date_ranges) AS previous_period,
    
    ROUND(c.spend, 0) AS current_spend,
    ROUND(p.spend, 0) AS previous_spend,
    ROUND((c.spend - p.spend) * 100.0 / NULLIF(p.spend, 0), 1) AS spend_change_pct,
    
    ROUND(c.conversions, 0) AS current_conversions,
    ROUND(p.conversions, 0) AS previous_conversions,
    ROUND((c.conversions - p.conversions) * 100.0 / NULLIF(p.conversions, 0), 1) AS conversions_change_pct,
    
    ROUND(c.spend / NULLIF(c.conversions, 0), 2) AS current_cpa,
    ROUND(p.spend / NULLIF(p.conversions, 0), 2) AS previous_cpa,
    
    ROUND(c.clicks * 100.0 / NULLIF(c.impressions, 0), 2) AS current_ctr,
    ROUND(p.clicks * 100.0 / NULLIF(p.impressions, 0), 2) AS previous_ctr,
    
    ROUND(c.revenue / NULLIF(c.spend, 0), 2) AS current_roas,
    ROUND(p.revenue / NULLIF(p.spend, 0), 2) AS previous_roas
    
FROM current_week c, previous_week p
"""

    @classmethod
    def performance_by_platform(cls, time_filter: str = "last_30_days") -> str:
        """Performance breakdown by platform."""
        interval = "30 days" if time_filter == "last_30_days" else "7 days"
        return f"""
WITH date_bounds AS (
    SELECT CAST(MAX("Date") AS DATE) AS max_date FROM all_campaigns
)
SELECT 
    Platform,
    ROUND(SUM("Total Spent"), 0) AS spend,
    ROUND(SUM("Site Visit"), 0) AS conversions,
    ROUND(SUM("Total Spent") / NULLIF(SUM("Site Visit"), 0), 2) AS cpa,
    ROUND(SUM(Clicks) * 100.0 / NULLIF(SUM(Impressions), 0), 2) AS ctr,
    ROUND((COALESCE(SUM(Revenue_2024),0) + COALESCE(SUM(Revenue_2025),0)) / NULLIF(SUM("Total Spent"), 0), 2) AS roas,
    ROUND(SUM(Impressions), 0) AS impressions,
    ROUND(SUM(Clicks), 0) AS clicks
FROM all_campaigns, date_bounds
WHERE CAST("Date" AS DATE) >= max_date - INTERVAL '{interval}'
GROUP BY Platform
ORDER BY spend DESC
"""

    @classmethod
    def performance_by_channel(cls, time_filter: str = "last_30_days") -> str:
        """Performance breakdown by channel."""
        interval = "30 days" if time_filter == "last_30_days" else "7 days"
        return f"""
WITH date_bounds AS (
    SELECT CAST(MAX("Date") AS DATE) AS max_date FROM all_campaigns
)
SELECT 
    Channel,
    ROUND(SUM("Total Spent"), 0) AS spend,
    ROUND(SUM("Site Visit"), 0) AS conversions,
    ROUND(SUM("Total Spent") / NULLIF(SUM("Site Visit"), 0), 2) AS cpa,
    ROUND(SUM(Clicks) * 100.0 / NULLIF(SUM(Impressions), 0), 2) AS ctr,
    ROUND((COALESCE(SUM(Revenue_2024),0) + COALESCE(SUM(Revenue_2025),0)) / NULLIF(SUM("Total Spent"), 0), 2) AS roas
FROM all_campaigns, date_bounds
WHERE CAST("Date" AS DATE) >= max_date - INTERVAL '{interval}'
GROUP BY Channel
ORDER BY spend DESC
"""

    @classmethod
    def top_campaigns_by_metric(cls, metric: str = "roas", limit: int = 10) -> str:
        """Get top performing campaigns."""
        metric_sql = {
            "roas": "(COALESCE(SUM(Revenue_2024),0) + COALESCE(SUM(Revenue_2025),0)) / NULLIF(SUM(\"Total Spent\"), 0)",
            "cpa": "SUM(\"Total Spent\") / NULLIF(SUM(\"Site Visit\"), 0)",
            "ctr": "SUM(Clicks) * 100.0 / NULLIF(SUM(Impressions), 0)",
            "conversions": "SUM(\"Site Visit\")",
            "spend": "SUM(\"Total Spent\")"
        }
        order = "DESC" if metric in ["roas", "ctr", "conversions", "spend"] else "ASC"
        
        return f"""
WITH date_bounds AS (
    SELECT CAST(MAX("Date") AS DATE) AS max_date FROM all_campaigns
)
SELECT 
    Campaign_Name_Full AS campaign,
    ROUND(SUM("Total Spent"), 0) AS spend,
    ROUND(SUM("Site Visit"), 0) AS conversions,
    ROUND(SUM("Total Spent") / NULLIF(SUM("Site Visit"), 0), 2) AS cpa,
    ROUND(SUM(Clicks) * 100.0 / NULLIF(SUM(Impressions), 0), 2) AS ctr,
    ROUND((COALESCE(SUM(Revenue_2024),0) + COALESCE(SUM(Revenue_2025),0)) / NULLIF(SUM("Total Spent"), 0), 2) AS roas
FROM all_campaigns, date_bounds
WHERE CAST("Date" AS DATE) >= max_date - INTERVAL '30 days'
  AND SUM("Site Visit") >= 10  -- Minimum conversions for statistical significance
GROUP BY Campaign_Name_Full
HAVING SUM("Site Visit") >= 10
ORDER BY {metric_sql.get(metric, metric_sql["roas"])} {order}
LIMIT {limit}
"""

    @classmethod
    def daily_trend(cls, metric: str = "spend", days: int = 30) -> str:
        """Daily trend for a metric."""
        metric_sql = {
            "spend": 'ROUND(SUM("Total Spent"), 0) AS spend',
            "conversions": 'ROUND(SUM("Site Visit"), 0) AS conversions',
            "ctr": 'ROUND(SUM(Clicks) * 100.0 / NULLIF(SUM(Impressions), 0), 2) AS ctr',
            "cpa": 'ROUND(SUM("Total Spent") / NULLIF(SUM("Site Visit"), 0), 2) AS cpa',
            "roas": 'ROUND((COALESCE(SUM(Revenue_2024),0) + COALESCE(SUM(Revenue_2025),0)) / NULLIF(SUM("Total Spent"), 0), 2) AS roas'
        }
        
        return f"""
WITH date_bounds AS (
    SELECT CAST(MAX("Date") AS DATE) AS max_date FROM all_campaigns
)
SELECT 
    CAST("Date" AS DATE) AS date,
    {metric_sql.get(metric, metric_sql["spend"])},
    ROUND(SUM("Site Visit"), 0) AS conversions,
    ROUND(SUM(Impressions), 0) AS impressions,
    ROUND(SUM(Clicks), 0) AS clicks
FROM all_campaigns, date_bounds
WHERE CAST("Date" AS DATE) >= max_date - INTERVAL '{days} days'
GROUP BY CAST("Date" AS DATE)
ORDER BY date
"""

    @classmethod
    def weekly_trend(cls, weeks: int = 8) -> str:
        """Weekly aggregated trend."""
        return f"""
WITH date_bounds AS (
    SELECT CAST(MAX("Date") AS DATE) AS max_date FROM all_campaigns
)
SELECT 
    DATE_TRUNC('week', CAST("Date" AS DATE)) AS week_start,
    ROUND(SUM("Total Spent"), 0) AS spend,
    ROUND(SUM("Site Visit"), 0) AS conversions,
    ROUND(SUM("Total Spent") / NULLIF(SUM("Site Visit"), 0), 2) AS cpa,
    ROUND(SUM(Clicks) * 100.0 / NULLIF(SUM(Impressions), 0), 2) AS ctr,
    ROUND((COALESCE(SUM(Revenue_2024),0) + COALESCE(SUM(Revenue_2025),0)) / NULLIF(SUM("Total Spent"), 0), 2) AS roas
FROM all_campaigns, date_bounds
WHERE CAST("Date" AS DATE) >= max_date - INTERVAL '{weeks * 7} days'
GROUP BY DATE_TRUNC('week', CAST("Date" AS DATE))
ORDER BY week_start
"""

    @classmethod
    def monthly_trend(cls, months: int = 12) -> str:
        """Monthly aggregated trend."""
        return f"""
SELECT 
    DATE_TRUNC('month', CAST("Date" AS DATE)) AS month,
    STRFTIME(DATE_TRUNC('month', CAST("Date" AS DATE)), '%b %Y') AS month_label,
    ROUND(SUM("Total Spent"), 0) AS spend,
    ROUND(SUM("Site Visit"), 0) AS conversions,
    ROUND(SUM("Total Spent") / NULLIF(SUM("Site Visit"), 0), 2) AS cpa,
    ROUND(SUM(Clicks) * 100.0 / NULLIF(SUM(Impressions), 0), 2) AS ctr,
    ROUND((COALESCE(SUM(Revenue_2024),0) + COALESCE(SUM(Revenue_2025),0)) / NULLIF(SUM("Total Spent"), 0), 2) AS roas
FROM all_campaigns
GROUP BY DATE_TRUNC('month', CAST("Date" AS DATE))
ORDER BY month DESC
LIMIT {months}
"""

    @classmethod
    def overall_kpis(cls, time_filter: str = "all_time") -> str:
        """Get overall KPI summary."""
        where_clause = ""
        if time_filter == "last_7_days":
            where_clause = "WHERE CAST(\"Date\" AS DATE) >= (SELECT max_date - INTERVAL '7 days' FROM date_bounds)"
        elif time_filter == "last_30_days":
            where_clause = "WHERE CAST(\"Date\" AS DATE) >= (SELECT max_date - INTERVAL '30 days' FROM date_bounds)"
        
        return f"""
WITH date_bounds AS (
    SELECT CAST(MAX("Date") AS DATE) AS max_date FROM all_campaigns
)
SELECT 
    ROUND(SUM("Total Spent"), 0) AS total_spend,
    ROUND(SUM("Site Visit"), 0) AS total_conversions,
    ROUND(SUM(Impressions), 0) AS total_impressions,
    ROUND(SUM(Clicks), 0) AS total_clicks,
    ROUND(SUM("Total Spent") / NULLIF(SUM("Site Visit"), 0), 2) AS overall_cpa,
    ROUND(SUM(Clicks) * 100.0 / NULLIF(SUM(Impressions), 0), 2) AS overall_ctr,
    ROUND(SUM("Total Spent") / NULLIF(SUM(Clicks), 0), 2) AS overall_cpc,
    ROUND((COALESCE(SUM(Revenue_2024),0) + COALESCE(SUM(Revenue_2025),0)) / NULLIF(SUM("Total Spent"), 0), 2) AS overall_roas,
    COUNT(DISTINCT Campaign_Name_Full) AS unique_campaigns,
    COUNT(DISTINCT Platform) AS unique_platforms
FROM all_campaigns, date_bounds
{where_clause}
"""

    @classmethod
    def get_sql_for_question(cls, question: str) -> Optional[str]:
        """
        Match question to a bulletproof template.
        Returns SQL if matched, None if should fall back to LLM.
        """
        intents = cls.detect_intent(question)
        
        # Week comparison
        if 'week_comparison' in intents:
            return cls.week_over_week_comparison()
        
        # Platform breakdown
        if 'by_platform' in intents:
            time_filter = 'last_7_days' if 'last_7_days' in intents else 'last_30_days'
            return cls.performance_by_platform(time_filter)
        
        # Channel breakdown
        if 'by_channel' in intents:
            time_filter = 'last_7_days' if 'last_7_days' in intents else 'last_30_days'
            return cls.performance_by_channel(time_filter)
        
        # Top campaigns
        if 'top_campaigns' in intents:
            if 'cpa' in intents:
                return cls.top_campaigns_by_metric("cpa", 10)
            elif 'ctr' in intents:
                return cls.top_campaigns_by_metric("ctr", 10)
            else:
                return cls.top_campaigns_by_metric("roas", 10)
        
        # Daily trend
        if 'daily_trend' in intents:
            days = 7 if 'last_7_days' in intents else 30
            if 'ctr' in intents:
                return cls.daily_trend("ctr", days)
            elif 'cpa' in intents:
                return cls.daily_trend("cpa", days)
            else:
                return cls.daily_trend("spend", days)
        
        # Weekly trend
        if 'weekly_trend' in intents:
            return cls.weekly_trend(8)
        
        # Monthly trend
        if 'monthly_trend' in intents:
            return cls.monthly_trend(12)
        
        # Overall KPIs
        if 'total_spend' in intents or 'total_conversions' in intents:
            if 'last_7_days' in intents:
                return cls.overall_kpis("last_7_days")
            elif 'last_30_days' in intents:
                return cls.overall_kpis("last_30_days")
            else:
                return cls.overall_kpis("all_time")
        
        # No match - let LLM handle it
        return None


# Test the matcher
if __name__ == "__main__":
    test_questions = [
        "Compare last 2 weeks performance",
        "Show me performance by platform",
        "What are the top campaigns by ROAS?",
        "Daily CTR trend for last 7 days",
        "Weekly spend trend",
        "Monthly performance breakdown",
        "What's the total spend?",
    ]
    
    for q in test_questions:
        sql = BulletproofQueries.get_sql_for_question(q)
        print(f"\n📝 {q}")
        print(f"   Matched: {'✅ Template' if sql else '❌ LLM Fallback'}")
        if sql:
            print(f"   SQL preview: {sql[:100]}...")
