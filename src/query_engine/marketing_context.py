"""
Marketing Domain Knowledge for NL-to-SQL Query Enhancement

Provides marketing context, metrics definitions, and business rules to improve
natural language to SQL query generation.
"""

# ====================================================================================
# CRITICAL MARKETING ANALYTICS PRINCIPLES (Rand Fishkin + Alex Freberg approach)
# These rules OVERRIDE generic SQL knowledge for marketing analytics
# ====================================================================================

MARKETING_ANALYTICS_PRINCIPLES = """
# CRITICAL MARKETING ANALYTICS RULES

## Rule 1: AGGREGATION - Never average pre-calculated rates
❌ NEVER: SELECT AVG(CTR), AVG(ROAS), AVG(CPA) - mathematically WRONG
✅ ALWAYS: Calculate from totals using SUM(numerator)/NULLIF(SUM(denominator), 0)

## Rule 2: TEMPORAL - Anchor to actual data, not current date
❌ NEVER: WHERE date >= CURRENT_DATE - INTERVAL '7 days'
✅ ALWAYS: WHERE date >= (SELECT MAX(date) FROM campaigns) - INTERVAL '7 days'

## Rule 3: NULL SAFETY - Every division must handle zero denominators
❌ NEVER: spend/conversions (will crash on zero conversions!)
✅ ALWAYS: spend/NULLIF(conversions, 0)

## Rule 4: PERCENTILES - Use percentiles, not arbitrary thresholds
❌ NEVER: WHERE ROAS > 3.0 (arbitrary, data-blind)
✅ BETTER: ORDER BY ROAS DESC LIMIT 10 (relative ranking)
✅ BEST: PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY ROAS) for top quartile

## Rule 5: FUNNEL VALIDATION - Use ONLY for data quality analysis
⚠️ IMPORTANT: Do NOT add funnel filters to simple aggregate queries!
❌ NEVER add funnel filter for "What's the CPA?" or total metrics - it excludes real data
✅ ONLY use funnel filter when user asks about data quality or anomalies:
   - "Are there any data issues?"
   - "Show me corrupted rows"
   - For these, use: WHERE clicks <= impressions AND conversions <= clicks

## Rule 6: SAMPLE SIZE - Include confidence indicators
✅ ALWAYS add to results:
   - SUM(conversions) AS sample_size
   - CASE WHEN SUM(conversions) < 100 THEN 'Low Confidence' ELSE 'High Confidence' END AS confidence

## Rule 7: DATE HANDLING - Dates are stored as proper datetime type
✅ The Date column is stored as datetime64 (proper DATE type)
✅ Use CAST("Date" AS DATE) for date operations - works correctly
✅ For date comparisons:
   - MAX: CAST(MAX("Date") AS DATE) AS max_date
   - Filter: WHERE CAST("Date" AS DATE) >= max_date - INTERVAL '7 days'
ℹ️ If dates appear as strings (DD/MM/YY), re-upload the data to fix.

## Rule 8: CAMPAIGN TYPE AWARENESS - Distinguish awareness vs conversion campaigns
❌ WRONG: Just using NULLIF hides zero-conversion campaigns
✅ ALWAYS: Include campaign_type classification when showing CPA:
   - Conversion campaigns: Has conversions > 0, CPA is meaningful
   - Awareness campaigns: Has impressions but 0 conversions, CPA = NULL (not applicable)
   - No activity: No impressions, exclude or flag

## Rule 9: DATE FORMATTING - Always include date in temporal queries
⚠️ MANDATORY: When query involves time periods, ALWAYS include a date column in results:
   - For DAILY data: Show date as-is (YYYY-MM-DD)
   - For WEEKLY data: Show DATE_TRUNC('week', CAST("Date" AS DATE)) AS week_start
   - For MONTHLY data: Use STRFTIME(CAST("Date" AS DATE), 'Mon-YY') AS month (e.g., 'Oct-25', 'Jan-24', 'Sep-23')
   
Templates:
```sql
-- Weekly aggregation with formatted date
DATE_TRUNC('week', CAST("Date" AS DATE)) AS week_start

-- Monthly aggregation with readable format  
STRFTIME(CAST("Date" AS DATE), 'Mon-YY') AS month
```

## Rule 10: CONSISTENT PERFORMANCE KPIs - Standard metrics for all performance queries
⚠️ MANDATORY: When user asks for "performance" at ANY granularity, ALWAYS include these standard KPIs:
   1. Total Spend (SUM("Total Spent"))
   2. Total Conversions (SUM("Site Visit"))
   3. CPA (SUM("Total Spent") / NULLIF(SUM("Site Visit"), 0))
   4. CTR (SUM(Clicks) * 100.0 / NULLIF(SUM(Impressions), 0))
   5. Impressions (SUM(Impressions))
   6. Clicks (SUM(Clicks))
   7. ROAS (SUM(Revenue_2024) / NULLIF(SUM("Total Spent"), 0))

This ensures consistent, comparable results across all aggregation levels (daily, weekly, monthly, by platform, by channel, etc.)

## METRIC CALCULATION TEMPLATES (Copy-paste these EXACTLY)

```sql
-- CTR (Click-Through Rate) - % of impressions that become clicks
SUM(clicks) * 100.0 / NULLIF(SUM(impressions), 0) AS CTR

-- CPC (Cost Per Click) - Average cost per click
SUM(spend) / NULLIF(SUM(clicks), 0) AS CPC

-- CPM (Cost Per Mille) - Cost per 1000 impressions
SUM(spend) * 1000.0 / NULLIF(SUM(impressions), 0) AS CPM

-- CPA (Cost Per Acquisition) - NUANCED VERSION with campaign type
SUM(spend) / NULLIF(SUM(conversions), 0) AS CPA,
CASE 
    WHEN SUM(conversions) > 0 THEN 'Conversion Campaign'
    WHEN SUM(impressions) > 0 THEN 'Awareness Only'
    ELSE 'No Activity'
END AS campaign_type

-- CVR (Conversion Rate) - % of clicks that convert
SUM(conversions) * 100.0 / NULLIF(SUM(clicks), 0) AS CVR

-- ROAS (Return on Ad Spend) - Revenue per dollar spent
SUM(revenue) / NULLIF(SUM(spend), 0) AS ROAS
```

## PERIOD-OVER-PERIOD COMPARISON TEMPLATE
⚠️ "Compare last 2 weeks" means: Week 1 (Dec 25-31) vs Week 2 (Dec 18-24)
```sql
WITH bounds AS (
    SELECT CAST(MAX("Date") AS DATE) AS max_date FROM campaigns
),
date_ranges AS (
    SELECT 
        max_date,
        max_date - INTERVAL '6 days' AS current_start,   -- Current week (7 days): Dec 25-31
        max_date - INTERVAL '7 days' AS previous_end,    -- Previous week end: Dec 24
        max_date - INTERVAL '13 days' AS previous_start  -- Previous week start: Dec 18
    FROM bounds
),
current_period AS (
    SELECT SUM("Total Spent") AS spend, SUM("Site Visit") AS conversions
    FROM campaigns, date_ranges
    WHERE CAST("Date" AS DATE) >= current_start AND CAST("Date" AS DATE) <= max_date
),
previous_period AS (
    SELECT SUM("Total Spent") AS spend, SUM("Site Visit") AS conversions
    FROM campaigns, date_ranges
    WHERE CAST("Date" AS DATE) >= previous_start AND CAST("Date" AS DATE) <= previous_end
)
SELECT 
    -- Date range labels
    (SELECT STRFTIME(current_start, '%b %d') || ' - ' || STRFTIME(max_date, '%b %d') FROM date_ranges) AS current_period,
    (SELECT STRFTIME(previous_start, '%b %d') || ' - ' || STRFTIME(previous_end, '%b %d') FROM date_ranges) AS previous_period,
    -- Spend comparison
    c.spend AS current_spend,
    p.spend AS previous_spend,
    ROUND((c.spend - p.spend) * 100.0 / NULLIF(p.spend, 0), 1) AS spend_change_pct,
    -- Conversions comparison
    c.conversions AS current_conversions,
    p.conversions AS previous_conversions,
    ROUND((c.conversions - p.conversions) * 100.0 / NULLIF(p.conversions, 0), 1) AS conversions_change_pct,
    -- Performance summary
    CASE WHEN c.spend < p.spend AND c.conversions >= p.conversions THEN '✅ Improved efficiency'
         WHEN c.spend > p.spend AND c.conversions <= p.conversions THEN '⚠️ Declining efficiency'
         ELSE '➡️ Stable' END AS performance_summary
FROM current_period c, previous_period p;
```

⚠️ CRITICAL for "compare X weeks" queries:
- ALWAYS include BOTH current_period AND previous_period date labels
- ALWAYS show side-by-side values (current_X, previous_X) 
- ALWAYS calculate percentage change: (current - previous) / previous * 100

## Rule 11: OPERATIONALIZE AMBIGUOUS TERMS - Define vague terms explicitly
⚠️ MANDATORY: When user uses ambiguous terms, operationalize them:

| Term | Definition |
|------|------------|
| "recently" | Last 7 days (vs baseline of previous 3 weeks) |
| "underperforming" | CPA increased >20% vs baseline, or ROAS decreased >20% |
| "best" / "worst" | ORDER BY metric DESC/ASC LIMIT 10 |
| "wasting money" | High spend + low/no conversions (CPA > 2x average) |
| "performing well" | CPA improved or ROAS improved vs baseline |

## Rule 12: YEAR-SPECIFIC REVENUE COLUMNS - Combine for ROAS
⚠️ CRITICAL: Revenue is split by year in this dataset:
- Revenue_2024: Only has values for 2024 data (zero for 2025)
- Revenue_2025: Only has values for 2025 data (zero for 2024)

✅ ALWAYS calculate total revenue as:
   COALESCE(Revenue_2024, 0) + COALESCE(Revenue_2025, 0) AS total_revenue

❌ NEVER use just Revenue_2024 - it will show 0 for current 2025 data!

Example ROAS calculation:
```sql
(COALESCE(SUM(Revenue_2024), 0) + COALESCE(SUM(Revenue_2025), 0)) / NULLIF(SUM("Total Spent"), 0) AS roas
```

## UNDERPERFORMING CAMPAIGNS TEMPLATE
⚠️ Use this template for queries like "underperforming campaigns", "campaigns that got worse":
```sql
WITH time_bounds AS (
    SELECT 
        STRPTIME(MAX("Date"), '%d/%m/%y')::DATE AS max_date,
        STRPTIME(MAX("Date"), '%d/%m/%y')::DATE - INTERVAL '6 days' AS week_start,
        STRPTIME(MAX("Date"), '%d/%m/%y')::DATE - INTERVAL '29 days' AS month_start
    FROM campaigns
),
recent_performance AS (
    SELECT 
        Campaign_Name_Full,
        SUM("Total Spent") / NULLIF(SUM("Site Visit"), 0) AS recent_CPA,
        SUM("Site Visit") AS recent_conversions
    FROM campaigns, time_bounds
    WHERE CAST("Date" AS DATE) >= week_start
    GROUP BY Campaign_Name_Full
),
baseline_performance AS (
    SELECT 
        Campaign_Name_Full,
        SUM("Total Spent") / NULLIF(SUM("Site Visit"), 0) AS baseline_CPA
    FROM campaigns, time_bounds
    WHERE CAST("Date" AS DATE) >= month_start 
      AND CAST("Date" AS DATE) < week_start
    GROUP BY Campaign_Name_Full
)
SELECT 
    r.Campaign_Name_Full,
    ROUND(r.recent_CPA, 2) AS recent_CPA,
    ROUND(b.baseline_CPA, 2) AS baseline_CPA,
    r.recent_conversions,
    ROUND((r.recent_CPA - b.baseline_CPA) / NULLIF(b.baseline_CPA, 0) * 100, 2) AS cpa_increase_pct,
    CASE 
        WHEN r.recent_conversions < 5 THEN 'Too few conversions to judge'
        WHEN r.recent_CPA > b.baseline_CPA * 1.5 THEN 'Significantly worse (50%+ increase)'
        WHEN r.recent_CPA > b.baseline_CPA * 1.2 THEN 'Moderately worse (20%+ increase)'
        WHEN r.recent_CPA > b.baseline_CPA THEN 'Slightly worse'
        ELSE 'Not underperforming'
    END AS performance_status
FROM recent_performance r
JOIN baseline_performance b ON r.Campaign_Name_Full = b.Campaign_Name_Full
WHERE r.recent_CPA > b.baseline_CPA
  AND r.recent_conversions >= 5
ORDER BY cpa_increase_pct DESC;
```
"""

MARKETING_GLOSSARY = """
# Marketing Analytics Glossary

## Key Metrics
- **ROAS (Return on Ad Spend)**: Revenue generated per dollar spent. Formula: Revenue / Spend
- **CPA (Cost Per Acquisition)**: Cost to acquire one customer. Formula: Spend / Conversions
- **CTR (Click-Through Rate)**: Percentage of impressions that result in clicks. Formula: (Clicks / Impressions) * 100
- **CPC (Cost Per Click)**: Average cost for each click. Formula: Spend / Clicks
- **CPM (Cost Per Mille)**: Cost per 1000 impressions. Formula: (Spend / Impressions) * 1000
- **Conversion Rate**: Percentage of clicks that convert. Formula: (Conversions / Clicks) * 100
- **CAC (Customer Acquisition Cost)**: Same as CPA
- **LTV (Lifetime Value)**: Total revenue expected from a customer over their lifetime

## Marketing Funnel Stages
- **Awareness**: Top of funnel (TOFU) - Building brand awareness, reaching new audiences
- **Consideration**: Middle of funnel (MOFU) - Engaging interested prospects, nurturing leads
- **Conversion**: Bottom of funnel (BOFU) - Converting prospects to customers

## Channels
- **SEM (Search Engine Marketing)**: Paid search ads (Google Ads, Bing Ads)
- **SOC (Social)**: Social media advertising (Facebook, Instagram, LinkedIn, Twitter, TikTok)
- **DIS (Display)**: Banner ads, programmatic advertising
- **VID (Video)**: YouTube, video advertising
- **EMAIL**: Email marketing campaigns

## Common Questions & Intent
- "Best/Top performing" = High ROAS or high conversions
- "Worst/Underperforming" = Low ROAS or high CPA
- "Wasting money" = High spend with low conversions
- "Funnel" = Analysis by funnel_stage (Awareness → Consideration → Conversion)
- "Trend" = Time-series analysis, usually monthly
- "Comparison" = Side-by-side metrics across platforms/channels

## Business Rules
- Exclude campaigns with spend < $100 for "top/worst" analysis (avoid noise)
- Default date range: Last 30 days if not specified
- "Recent" = Last 7 days
- "This month" = Current calendar month
- "Last month" = Previous calendar month
"""

QUERY_CONTEXT = """
# Query Generation Guidelines

## When analyzing performance:
- "Best" campaigns = ORDER BY roas DESC or conversions DESC
- "Worst" campaigns = ORDER BY roas ASC or cpa DESC (with minimum spend filter)
- Always include LIMIT for top/bottom queries (default: 10)

## Funnel Analysis:
- Table name is 'all_campaigns'
- Key columns: campaign_name, platform, channel, spend, impressions, clicks, conversions, ctr, cpc, cpa, roas, date, funnel_stage, objective, device_type
- Group by funnel_stage column
- Order: Awareness → Consideration → Conversion
- Calculate drop-off rates between stages

## Time-based queries:
- Use DATE_TRUNC('month', CAST(date AS TIMESTAMP)) for monthly trends
- Use DATE_TRUNC('week', date) for weekly trends
- Always ORDER BY date/month DESC for trends

## Filters:
- Use NULLIF() to avoid division by zero
- Common metrics: CTR = (clicks/impressions)*100, CPC = spend/clicks, CPA = spend/conversions
- Funnel stages: 'Awareness', 'Consideration', 'Conversion'
- Device types are in additional_data JSON field, extract with: json_extract(additional_data, '$.device_type')
- Exclude NULL or 'Unknown' values in funnel_stage for funnel analysis
- For "wasting money" queries: spend > 5000 AND conversions < 100
- For platform/channel comparison: GROUP BY platform or channel

## Metrics to include:
- Always calculate CTR, CPC, CPA when relevant columns exist
- Include conversion_rate for funnel analysis
- Show both absolute numbers (spend, conversions) and rates (CTR, ROAS)
"""

def get_marketing_context_for_nl_to_sql(schema_info: dict = None) -> str:
    """
    Get marketing domain context to enhance NL-to-SQL query generation.
    Now DATA-AWARE - analyzes actual schema to provide relevant context.
    
    Args:
        schema_info: Schema information from the query engine
        
    Returns:
        Formatted context string to add to NL-to-SQL prompt
    """
    # Base marketing glossary (always included)
    base_glossary = """
# Marketing Analytics Glossary

## Key Metrics
- **ROAS (Return on Ad Spend)**: Revenue generated per dollar spent. Formula: Revenue / Spend
- **CPA (Cost Per Acquisition)**: Cost to acquire one customer. Formula: Spend / Conversions
- **CTR (Click-Through Rate)**: Percentage of impressions that result in clicks. Formula: (Clicks / Impressions) * 100
- **CPC (Cost Per Click)**: Average cost for each click. Formula: Spend / Clicks
- **CPM (Cost Per Mille)**: Cost per 1000 impressions. Formula: (Spend / Impressions) * 1000
- **Conversion Rate**: Percentage of clicks that convert. Formula: (Conversions / Clicks) * 100
- **CAC (Customer Acquisition Cost)**: Same as CPA
- **LTV (Lifetime Value)**: Total revenue expected from a customer over their lifetime

## Marketing Funnel Stages
- **Awareness / TOFU (Top of Funnel)**: Building brand awareness, reaching new audiences
- **Consideration / MOFU (Middle of Funnel)**: Engaging interested prospects, nurturing leads
- **Conversion / BOFU (Bottom of Funnel)**: Converting prospects to customers

## Common Channels
- **SEM (Search Engine Marketing)**: Paid search ads (Google Ads, Bing Ads)
- **SOC (Social)**: Social media advertising (Facebook, Instagram, LinkedIn, Twitter, TikTok)
- **DIS (Display)**: Banner ads, programmatic advertising
- **VID (Video)**: YouTube, video advertising
- **EMAIL**: Email marketing campaigns
"""

    # If no schema info, return base glossary only
    if not schema_info:
        return f"{base_glossary}\n\n{QUERY_CONTEXT}"
    
    # Analyze actual data to provide relevant context
    columns = schema_info.get('columns', [])
    sample_data = schema_info.get('sample_data', [])
    
    # Build data-specific context
    data_context = "\n## YOUR DATA CONTEXT\n"
    
    # 1. Identify available metrics
    available_metrics = []
    metric_mapping = {
        'spend': ['spend', 'cost', 'total_spent', 'budget'],
        'impressions': ['impressions', 'views', 'reach'],
        'clicks': ['clicks', 'link_clicks'],
        'conversions': ['conversions', 'site_visit', 'purchases', 'leads'],
        'revenue': ['revenue', 'conversion_value', 'sales'],
        'roas': ['roas', 'return_on_ad_spend']
    }
    
    for metric_type, possible_names in metric_mapping.items():
        for col in columns:
            if any(name in col.lower() for name in possible_names):
                available_metrics.append(f"- **{metric_type.upper()}**: Use column `{col}`")
                break
    
    if available_metrics:
        data_context += "\n**Available Metrics in Your Data**:\n" + "\n".join(available_metrics) + "\n"
    
    # 2. Identify dimensions
    dimension_cols = []
    dimension_keywords = ['platform', 'channel', 'campaign', 'funnel', 'stage', 'device', 'ad_type', 'audience']
    for col in columns:
        if any(kw in col.lower() for kw in dimension_keywords):
            dimension_cols.append(col)
    
    if dimension_cols:
        data_context += f"\n**Available Dimensions**: {', '.join([f'`{col}`' for col in dimension_cols])}\n"
    
    # 3. Identify funnel stages if available
    funnel_col = next((col for col in columns if 'funnel' in col.lower() or 'stage' in col.lower()), None)
    if funnel_col and sample_data:
        funnel_values = set()
        for row in sample_data:
            val = row.get(funnel_col)
            if val and val != 'Unknown':
                funnel_values.add(val)
        
        if funnel_values:
            data_context += f"\n**Funnel Stages in Your Data**: {', '.join(sorted(funnel_values))}\n"
            data_context += f"- Use column `{funnel_col}` for funnel analysis\n"
    
    # 4. Identify platforms/channels
    platform_col = next((col for col in columns if 'platform' in col.lower()), None)
    if platform_col and sample_data:
        platforms = set()
        for row in sample_data:
            val = row.get(platform_col)
            if val:
                platforms.add(val)
        
        if platforms:
            data_context += f"\n**Platforms in Your Data**: {', '.join(sorted(platforms))}\n"
            data_context += "- Use these EXACT platform names in queries\n"
    
    channel_col = next((col for col in columns if 'channel' in col.lower()), None)
    if channel_col and sample_data:
        channels = set()
        for row in sample_data:
            val = row.get(channel_col)
            if val:
                channels.add(val)
        
        if channels:
            data_context += f"\n**Channels in Your Data**: {', '.join(sorted(channels))}\n"
            data_context += "- Use these EXACT channel names in queries\n"
    
    # 5. Date range context
    date_col = next((col for col in columns if any(kw in col.lower() for kw in ['date', 'week', 'month', 'period'])), None)
    if date_col:
        data_context += f"\n**Time Column**: Use `{date_col}` for date-based queries\n"
    
    # Combine everything
    smart_intent_guide = """
## 🧠 INTELLIGENT QUERY UNDERSTANDING (Steve Jobs Level)

**Think like a user, not a database**. Understand INTENT, not just keywords.

### Smart Intent-to-Column Mapping
When user mentions these concepts, find the CLOSEST matching column:
- **"device/mobile/desktop/tablet"** → device_type, device, device_name, platform_type
- **"funnel/stage/TOFU/MOFU/BOFU"** → funnel_stage, stage, marketing_stage
- **"campaign/ad"** → campaign_name, campaign_id, ad_name
- **"platform/network"** → platform, ad_platform, network
- **"channel/medium"** → channel, marketing_channel, medium
- **"time/date/trend"** → date, week, month, period

### Time Period Intelligence
When user asks about time comparisons, understand these patterns:
- **"last month vs this month"** → Filter by current month and previous month, compare metrics
- **"period over period" / "vs previous period"** → Compare current period to equivalent previous period
- **"week over week" / "WoW"** → Compare this week to last week
- **"month over month" / "MoM"** → Compare this month to last month
- **"year over year" / "YoY"** → Compare this year to last year
- **"last 7 days vs previous 7 days"** → Two 7-day windows for comparison
- **"Q1 vs Q2"** → Quarter comparison
- **"compare last 3 months"** → Show each of last 3 months side by side

**How to handle period comparisons**:
1. Identify the time column (date, week, month, period)
2. Determine the two periods to compare
3. Use CASE statements or CTEs to separate periods
4. Calculate metrics for each period
5. Show side-by-side comparison with % change

### Intelligent Behavior
1. **Match semantically** - Find closest column even if names don't match exactly
2. **Understand "compare by X"** - Group by the dimension X and show key metrics
3. **Smart defaults** - "performance" = spend + conversions + CTR + ROAS
4. **Flexible** - If exact column missing, use next best alternative
5. **Explain** - If can't match, tell user what IS available
6. **Time-aware** - Recognize period comparisons and generate appropriate date filters

### Edge Case Handling (Production-Ready)

**Missing Data**:
- If device_type column doesn't exist → Explain "Your data doesn't have device information. Try: 'compare by platform' or 'compare by channel'"
- If funnel_stage column doesn't exist → Suggest "Try analyzing by platform, channel, or campaign instead"
- If date column doesn't exist → Explain "Time-based analysis not available. Try: 'compare platforms' or 'top campaigns'"

**Ambiguous Queries**:
- "show performance" (too vague) → Ask "Performance by what? Try: 'performance by platform', 'performance by channel', or 'top performing campaigns'"
- "compare" (no dimension) → Suggest "Compare what? Try: 'compare platforms', 'compare channels', or 'compare last month vs this month'"

**Invalid Time Periods**:
- "last month" when data only has current month → Explain "Only current month data available. Showing current month performance instead"
- "Q1 vs Q2" when data only has Q1 → Show Q1 data and explain Q2 not available
- Future dates requested → Explain "Future data not available. Showing latest available data"

**Empty Results**:
- Query returns 0 rows → Explain why (e.g., "No campaigns match these criteria. Try broader filters or different time period")
- All values are NULL → Explain "Data incomplete for this metric. Try different metrics like spend or impressions"

**Data Quality Issues**:
- Many NULL/Unknown values → Filter them out automatically and mention in response
- Outliers (e.g., ROAS > 1000) → Include but flag as potential data quality issue
- Zero spend campaigns → Exclude from ROAS/CPA calculations to avoid division by zero

**Fallback Strategies**:
1. **Column not found** → Search for similar column names, suggest alternatives
2. **No data for period** → Expand date range or suggest available periods
3. **Metric can't be calculated** → Explain why and suggest alternative metrics
4. **Too many results** → Automatically add LIMIT and offer to show more
5. **Complex query fails** → Simplify and retry with basic version

**User-Friendly Responses**:
- Always explain what you did and why
- If you made assumptions, state them clearly
- Provide actionable next steps
- Show what data IS available, not just what's missing
"""
    
    return f"""
{MARKETING_ANALYTICS_PRINCIPLES}

{base_glossary}

{data_context}

{smart_intent_guide}

{QUERY_CONTEXT}

IMPORTANT: Use this marketing knowledge to:
1. **Follow CRITICAL RULES above** - They override generic SQL patterns
2. **Understand intent, not just keywords** - Be Steve Jobs level intuitive
3. **Match semantically** - Find CLOSEST column to user's intent
4. **Be flexible** - Work with what's available, don't fail on exact matches
5. **Think holistically** - Consider full question context
6. Use EXACT column names from available dimensions
"""


def get_error_context(error_type: str, details: dict) -> str:
    """
    Generate helpful, context-aware error messages.
    
    Args:
        error_type: Type of error (e.g., 'no_data', 'invalid_column', 'sql_error')
        details: Error details
        
    Returns:
        User-friendly error message with suggestions
    """
    if error_type == 'no_data':
        return """
No data found matching your query. 

**Suggestions**:
- Try a broader date range
- Check if the platform/channel name is correct
- Try one of the suggested questions below
"""
    
    elif error_type == 'invalid_column':
        available_cols = details.get('available_columns', [])
        requested_col = details.get('requested_column', '')
        return f"""
Column '{requested_col}' not found in the data.

**Available columns**: {', '.join(available_cols)}

**Tip**: Try asking about platforms, channels, spend, conversions, or ROAS.
"""
    
    elif error_type == 'sql_error':
        return """
I had trouble understanding your question.

**Try asking**:
- "Show funnel analysis"
- "Which platform has the best ROAS?"
- "Show me top performing campaigns"
- "Compare channels"
"""
    
    elif error_type == 'timeout':
        return """
Your query is taking longer than expected.

**This might help**:
- Try a shorter date range
- Ask about specific platforms or channels
- Use one of the suggested questions for faster results
"""
    
    else:
        return "Something went wrong. Please try rephrasing your question or use one of the suggested questions."
