"""
Natural Language to SQL Query Engine
Converts natural language questions into SQL queries using LLM
"""
import duckdb
import pandas as pd
from typing import Dict, Any, Optional, List
from openai import OpenAI
import os
from loguru import logger
import sys

from .sql_knowledge import SQLKnowledgeHelper
from src.utils.anthropic_helpers import create_anthropic_client
from .query_optimizer import QueryOptimizer
from .multi_table_manager import MultiTableManager
from .template_generator import TemplateGenerator
from .safe_query import SafeQueryExecutor
from .bulletproof_queries import BulletproofQueries

# Configure logger to also write to file
logger.add("query_debug.log", rotation="1 MB", level="INFO")

# Try to import Google Gemini
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-generativeai not installed. Install with: pip install google-generativeai")

# Try to import Groq (FREE fallback)
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("groq not installed. Install with: pip install groq")

# Try to import DeepSeek (FREE, excellent at coding)
DEEPSEEK_AVAILABLE = True  # Uses OpenAI-compatible API


class NaturalLanguageQueryEngine:
    """Engine to convert natural language questions to SQL queries and execute them."""
    
    def __init__(self, api_key: str):
        """
        Initialize the query engine.
        
        Args:
            api_key: OpenAI API key for LLM
        """
        self.openai_client = OpenAI(api_key=api_key)
        
        # Setup available models in priority order
        self.available_models = []
        self.sql_helper = SQLKnowledgeHelper(enable_hybrid=True)
        
        # 1. Gemini 1.5 Flash (FREE & FAST)
        google_key = os.getenv('GOOGLE_API_KEY')
        if google_key and GEMINI_AVAILABLE:
            genai.configure(api_key=google_key)
            self.available_models.append(('gemini', 'gemini-2.5-flash'))
            logger.info("Tier 1: Gemini 2.5 Flash (FREE)")
        
        # 2. DeepSeek (FREE CODING SPECIALIST)
        deepseek_key = os.getenv('DEEPSEEK_API_KEY')
        if deepseek_key and DEEPSEEK_AVAILABLE:
            self.deepseek_client = OpenAI(
                api_key=deepseek_key,
                base_url="https://api.deepseek.com"
            )
            self.available_models.append(('deepseek', 'deepseek-chat'))
            logger.info("Tier 2: DeepSeek Chat (FREE CODING SPECIALIST)")
        
        # 3. OpenAI GPT-4o
        if self.openai_client:
            self.available_models.append(('openai', 'gpt-4o'))
            logger.info("Tier 3: OpenAI GPT-4o")
        
        # 4. Claude 3.5 Sonnet
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if anthropic_key and anthropic_key.startswith('sk-ant-'):
            self.anthropic_client = create_anthropic_client(anthropic_key)
            if self.anthropic_client:
                self.available_models.append(('claude', 'claude-3-5-sonnet-latest'))
                logger.info("Tier 4: Claude 3.5 Sonnet")
            else:
                logger.warning("Anthropic client unavailable. Skipping Claude tier.")
        
        # 5. Groq (ULTIMATE FREE FALLBACK)
        groq_key = os.getenv('GROQ_API_KEY')
        if groq_key and GROQ_AVAILABLE:
            self.groq_client = Groq(api_key=groq_key)
            self.available_models.append(('groq', 'llama-3.3-70b-versatile'))
            logger.info("Tier 5: Groq Llama 3.3 70B (FREE & SUPER FAST)")
        
        logger.info(f"Available models: {[m[0] for m in self.available_models]}")
        
        self.conn = None
        self.schema_info = None
        self.optimizer: Optional[QueryOptimizer] = None
        self.multi_table_manager: Optional[MultiTableManager] = None
        self.template_generator: Optional[TemplateGenerator] = None
        logger.info("Initialized NaturalLanguageQueryEngine")
    
    def load_data(self, df: pd.DataFrame, table_name: str = "campaigns"):
        """
        Load data into DuckDB.
        
        Args:
            df: DataFrame with campaign data
            table_name: Name for the table
        """
        from .safe_query import SafeQueryExecutor
        
        # Sanitize table name to prevent SQL injection
        table_name = SafeQueryExecutor.sanitize_identifier(table_name)
        
        # Convert Date-related columns to datetime if they exist
        df_copy = df.copy()
        
        # Detect date-related columns (date, week, week range, day, month, etc.)
        date_keywords = ['date', 'week', 'day', 'month', 'year', 'time', 'period']
        date_columns = [col for col in df_copy.columns 
                       if any(keyword in col.lower() for keyword in date_keywords)]
        
        for col in date_columns:
            try:
                df_copy[col] = pd.to_datetime(df_copy[col], errors='coerce')
                logger.info(f"Converted {col} to datetime")
            except:
                logger.warning(f"Could not convert {col} to datetime")
        
        self.conn = duckdb.connect(':memory:')
        self.conn.register(table_name, df_copy)
        
        # Initialize optimizer, multi-table manager, and template generator
        self.optimizer = QueryOptimizer(self.conn)
        self.multi_table_manager = MultiTableManager(self.conn)
        self.template_generator = TemplateGenerator(df_copy.columns.tolist())
        
        # Register primary table with multi-table manager
        # Try to detect primary key
        primary_key = None
        for col in df_copy.columns:
            if 'id' in col.lower() and col.lower() in ['id', 'campaign_id', f'{table_name}_id']:
                primary_key = col
                break
        
        self.multi_table_manager.register_table(
            name=table_name,
            df=df_copy,
            primary_key=primary_key,
            description=f"Main {table_name} table"
        )
        
        # Store schema information
        self.schema_info = {
            "table_name": table_name,
            "columns": df_copy.columns.tolist(),
            "dtypes": df_copy.dtypes.to_dict(),
            "sample_data": df_copy.head(3).to_dict('records')
        }
        
        logger.info(f"Loaded {len(df_copy)} rows into table '{table_name}'")

    def load_parquet_data(self, parquet_path: str, table_name: str = "campaigns"):
        """
        Load data from Parquet file into DuckDB.
        
        Args:
            parquet_path: Path to the Parquet file
            table_name: Name for the table
        """
        # Validate and sanitize inputs
        table_name = SafeQueryExecutor.sanitize_identifier(table_name)
        parquet_path = SafeQueryExecutor.validate_file_path(parquet_path, allowed_extensions=['.parquet'])

        self.conn = duckdb.connect(':memory:')
        
        # Register the parquet file as a view using string injection (DuckDB does not support ? in CREATE VIEW/read_parquet)
        # Path is already validated by validate_file_path above
        self.conn.execute(f"CREATE VIEW {table_name} AS SELECT * FROM read_parquet('{parquet_path}')")  # nosec B608
        
        # Initialize optimizer, multi-table manager, and template generator
        self.optimizer = QueryOptimizer(self.conn)
        self.multi_table_manager = MultiTableManager(self.conn)
        self.template_generator = TemplateGenerator(self.conn.execute(f"DESCRIBE {table_name}").df()["column_name"].tolist())
        
        # Get schema info from a sample (table_name is sanitized, safe to use)
        sample_df = self.conn.execute(f"SELECT * FROM {table_name} LIMIT 5").df()  # nosec B608
        
        # Store schema information
        self.schema_info = {
            "table_name": table_name,
            "columns": sample_df.columns.tolist(),
            "dtypes": sample_df.dtypes.to_dict(),
            "sample_data": sample_df.head(3).to_dict('records')
        }
        
        # Also register with multi-table manager for complex queries
        # IMPORTANT: Use skip_db_registration=True to avoid shadowing our full Parquet view with a 5-row sample
        self.multi_table_manager.register_table(
            name=table_name,
            df=sample_df, # Just use sample for schema detection in manager
            description=f"Persistent {table_name} table from Parquet",
            skip_db_registration=True
        )
        
        logger.info(f"Registered Parquet file {parquet_path} as table '{table_name}'")
    
    def load_additional_table(
        self,
        df: pd.DataFrame,
        table_name: str,
        primary_key: Optional[str] = None,
        description: Optional[str] = None
    ):
        """
        Load an additional table for multi-table queries.
        
        Args:
            df: DataFrame to load
            table_name: Name for the table
            primary_key: Primary key column
            description: Table description
        """
        if not self.multi_table_manager:
            raise ValueError("Call load_data() first to initialize the query engine")
        
        # Convert date columns
        df_copy = df.copy()
        date_keywords = ['date', 'week', 'day', 'month', 'year', 'time', 'period']
        date_columns = [col for col in df_copy.columns 
                       if any(keyword in col.lower() for keyword in date_keywords)]
        
        for col in date_columns:
            try:
                df_copy[col] = pd.to_datetime(df_copy[col], errors='coerce')
                logger.info(f"Converted {col} to datetime in {table_name}")
            except:
                logger.warning(f"Could not convert {col} to datetime in {table_name}")
        
        # Register with multi-table manager
        self.multi_table_manager.register_table(
            name=table_name,
            df=df_copy,
            primary_key=primary_key,
            description=description or f"{table_name} table"
        )
        
        logger.info(f"Loaded additional table '{table_name}' with {len(df_copy)} rows")
    
    def auto_detect_relationships(self) -> List[Dict[str, Any]]:
        """
        Auto-detect relationships between loaded tables.
        
        Returns:
            List of detected relationships
        """
        if not self.multi_table_manager:
            raise ValueError("No tables loaded")
        
        detected = self.multi_table_manager.auto_detect_relationships()
        
        # Add to relationships list
        self.multi_table_manager.relationships.extend(detected)
        
        logger.info(f"Auto-detected {len(detected)} relationships")
        return [r.to_dict() for r in detected]
    
    def validate_relationships(self) -> Dict[str, Any]:
        """
        Validate all relationships.
        
        Returns:
            Dictionary with validation results
        """
        if not self.multi_table_manager:
            return {'validated': 0, 'failed': 0, 'results': []}
        
        results = []
        validated_count = 0
        failed_count = 0
        
        for rel in self.multi_table_manager.relationships:
            is_valid, message = self.multi_table_manager.validate_relationship(rel)
            results.append({
                'relationship': rel.to_dict(),
                'valid': is_valid,
                'message': message
            })
            if is_valid:
                validated_count += 1
            else:
                failed_count += 1
        
        return {
            'validated': validated_count,
            'failed': failed_count,
            'results': results
        }


    def _get_schema_description(self) -> str:
        """Return a formatted schema description for prompt injection."""
        if not self.schema_info:
            raise ValueError(
                "Schema information not available. Call load_data() before asking questions."
            )

        columns = self.schema_info.get("columns", [])
        dtypes = self.schema_info.get("dtypes", {})
        sample_rows = self.schema_info.get("sample_data", [])
        table_name = self.schema_info.get("table_name", "campaigns")

        lines = [f"Table: {table_name}"]
        if columns:
            lines.append("Columns:")
            for col in columns:
                dtype = dtypes.get(col)
                lines.append(f"- {col} ({dtype})")
        
        # Include unique values for key categorical columns (CRITICAL for filters)
        if self.conn:
            try:
                from .safe_query import SafeQueryExecutor
                
                categorical_cols = ['platform', 'channel', 'funnel', 'ad_type', 'device_type', 'campaign_name']
                lines.append("\nIMPORTANT - Actual values in data (use these EXACTLY for filters):")
                for col in columns:
                    col_lower = col.lower().replace(' ', '_')
                    if col_lower in categorical_cols or any(cat in col_lower for cat in categorical_cols):
                        try:
                            # Sanitize identifiers to prevent SQL injection
                            safe_table = SafeQueryExecutor.sanitize_identifier(table_name)
                            # Column names with spaces need quotes, but sanitize first
                            if ' ' in col:
                                # For columns with spaces, use quotes but validate the content
                                # DuckDB allows quoted identifiers
                                safe_col = col  # Keep original for display
                                unique_query = f'SELECT DISTINCT "{col}" FROM {safe_table} LIMIT 20'  # nosec B608
                            else:
                                safe_col = SafeQueryExecutor.sanitize_identifier(col)
                                unique_query = f'SELECT DISTINCT {safe_col} FROM {safe_table} LIMIT 20'  # nosec B608
                            
                            unique_df = self.conn.execute(unique_query).fetchdf()
                            if not unique_df.empty:
                                unique_vals = unique_df.iloc[:, 0].dropna().tolist()[:10]
                                if unique_vals:
                                    lines.append(f"  {col}: {unique_vals}")
                        except Exception as col_error:
                            logger.debug(f"Could not get unique values for {col}: {col_error}")
            except Exception as e:
                logger.warning(f"Could not get unique values: {e}")

        if sample_rows:
            lines.append("\nSample rows:")
            for row in sample_rows:
                lines.append(f"- {row}")

        return "\n".join(lines)

    def generate_sql(self, question: str) -> str:
        """
        Convert natural language question to SQL query.
        
        Args:
            question: Natural language question
            
        Returns:
            SQL query string
        """
        schema_description = self._get_schema_description()
        sql_context = self.sql_helper.build_context(question, self.schema_info)
        
        # Get marketing domain context for better query understanding (DATA-AWARE)
        from src.query_engine.marketing_context import get_marketing_context_for_nl_to_sql
        marketing_context = get_marketing_context_for_nl_to_sql(self.schema_info)
        
        # ====================================================================================
        # PHASE 3: HYBRID RETRIEVAL - Intent classification and SQL hints
        # ====================================================================================
        from src.query_engine.hybrid_retrieval import analyze_question
        
        analysis = analyze_question(question)
        intent = analysis['intent'].value
        complexity = analysis['complexity'].value
        entities = analysis['entities']
        
        # Generate SQL hints based on analysis
        sql_hints = []
        mandatory_group_by = ""
        mandatory_granularity = ""
        
        if entities.group_by:
            sql_hints.append(f"GROUP BY: {', '.join(entities.group_by)}")
            # Map semantic terms to actual column names
            group_by_mapping = {
                'platform': 'Platform',
                'channel': 'Channel', 
                'device': '"Device Type"',
                'funnel': 'Funnel',
                'campaign': 'Campaign_Name_Full',
            }
            actual_cols = [group_by_mapping.get(g, g) for g in entities.group_by]
            mandatory_group_by = f"\n⚠️ MANDATORY: The user said 'by {', '.join(entities.group_by)}' - YOU MUST GROUP BY {', '.join(actual_cols)}"
        
        # Handle granularity (daily/weekly/monthly) - CRITICAL for SQL structure
        if entities.granularity:
            granularity_sql = {
                'daily': "DATE_TRUNC('day', STRPTIME(\"Date\", '%d/%m/%y')::DATE) AS date",
                'weekly': "DATE_TRUNC('week', STRPTIME(\"Date\", '%d/%m/%y')::DATE) AS week_start",
                'monthly': "STRFTIME(STRPTIME(\"Date\", '%d/%m/%y')::DATE, 'Mon-YY') AS month",
            }
            sql_hints.append(f"GRANULARITY: {entities.granularity}")
            mandatory_granularity = f"""
⚠️ MANDATORY GRANULARITY: The user asked for {entities.granularity.upper()} data.
YOU MUST:
1. Include this in SELECT: {granularity_sql.get(entities.granularity, '')}
2. GROUP BY the date column with the same DATE_TRUNC
3. ORDER BY the date to show chronological trend"""
        
        if entities.metrics:
            sql_hints.append(f"METRICS: {', '.join(entities.metrics)}")
        if entities.time_period:
            sql_hints.append(f"TIME FILTER: {entities.time_period}")
        if entities.limit:
            sql_hints.append(f"LIMIT: {entities.limit}")
        if entities.order_by:
            sql_hints.append(f"ORDER: {entities.order_by}")
        
        query_analysis = f"""
⚠️ CRITICAL QUERY ANALYSIS - FOLLOW THESE INSTRUCTIONS:
- Intent: {intent.upper()}
- Complexity: {complexity.upper()}
- Required SQL patterns: {', '.join(sql_hints) if sql_hints else 'Standard aggregation'}
{mandatory_group_by}{mandatory_granularity}
"""
        
        logger.info(f"=== GENERATING SQL FOR QUESTION: {question} ===")
        logger.info(f"Intent: {intent}, Complexity: {complexity}")
        logger.info(f"Entities - GroupBy: {entities.group_by}, Metrics: {entities.metrics}")
        logger.info(f"Schema info available: {self.schema_info is not None}")
        if self.schema_info:
            logger.info(f"Columns: {self.schema_info.get('columns', [])}")
        logger.info(f"Schema description length: {len(schema_description)} chars")
        
        prompt = f"""You are a SQL expert specializing in marketing campaign analytics. Convert the following natural language question into a DuckDB SQL query.

{query_analysis}

{marketing_context}

Database Schema:
{schema_description}

SQL Knowledge & Reference:
{sql_context}

CRITICAL AGGREGATION RULES - NEVER VIOLATE:

For calculated/rate metrics (CTR, CPC, CPM, CPA, ROAS, Conversion Rate), you MUST:
* ALWAYS compute from aggregates: SUM(numerator) / SUM(denominator)
- NEVER use AVG() on pre-calculated rate columns

Examples:
- CTR = (SUM(Clicks) / NULLIF(SUM(Impressions), 0)) * 100
- CPC = SUM(Spend) / NULLIF(SUM(Clicks), 0)
- CPM = (SUM(Spend) / NULLIF(SUM(Impressions), 0)) * 1000
- CPA = SUM(Spend) / NULLIF(SUM(Conversions), 0)
- ROAS = SUM(Revenue) / NULLIF(SUM(Spend), 0)  [or use Conversion_Value if Revenue not available]
- Conversion_Rate = (SUM(Conversions) / NULLIF(SUM(Clicks), 0)) * 100

TEMPORAL COMPARISON PATTERNS (ANCHOR ON DATA, NOT CURRENT_DATE):

Always anchor relative time windows on the *latest date present in the data*, not on CURRENT_DATE.

CRITICAL: DATE COLUMN FLEXIBILITY
- The date column may NOT be named "Date"
- Look for columns with these keywords: date, week, week_range, week range, day, month, year, time, period
- Common examples: "Week Range", "Week", "Date Range", "Day", "Month", "Period"
- ALWAYS check the schema for the actual date column name before writing queries
- Use the EXACT column name from the schema (case-sensitive)

1) Find the campaign end date (max_date) from the table first, using a CTE pattern like:

   WITH bounds AS (
       SELECT MAX([actual_date_column_name]) AS max_date
       FROM campaigns
   )
   
   Replace [actual_date_column_name] with the real column name from the schema.

2) Then express natural language time windows relative to bounds.max_date (campaign life):

- "last 2 weeks"      -> [date_col] >= max_date - INTERVAL 14 DAY
- "previous 2 weeks"  -> [date_col] >= max_date - INTERVAL 28 DAY AND [date_col] < max_date - INTERVAL 14 DAY
- "last month"        -> [date_col] >= DATE_TRUNC('month', max_date - INTERVAL 1 MONTH)
- "last 2 months"     -> [date_col] >= max_date - INTERVAL 2 MONTH
- "last 6 months"     -> [date_col] >= max_date - INTERVAL 6 MONTH
- "last 2 years"      -> [date_col] >= max_date - INTERVAL 2 YEAR
- "couple of months"  -> treat as 2 months (use 2 MONTH window)
- "week-over-week"    -> GROUP BY DATE_TRUNC('week', [date_col])
- "month-over-month"  -> GROUP BY DATE_TRUNC('month', [date_col])
- "Q3 vs Q2"          -> use QUARTER([date_col]) or DATE_TRUNC('quarter', [date_col])
- "year-over-year"    -> compare same period across different years using YEAR([date_col])
- "by day"            -> GROUP BY [date_col] (use the actual date column name)
- "by week"           -> GROUP BY [date_col] or DATE_TRUNC('week', [date_col])
- "by month"          -> GROUP BY DATE_TRUNC('month', [date_col])

EXAMPLE: If schema has "Week Range" column and user asks "show total spend by day":
SELECT "Week Range", SUM(Cost) AS Total_Spend
FROM campaigns
GROUP BY "Week Range"
ORDER BY "Week Range"

For comparisons ("last X vs previous X") you should:
- Use a CTE that joins every row with max_date from bounds
- Create a period label using CASE WHEN, for example for last 2 months vs previous 2 months:

   WITH bounds AS (
       SELECT MAX(Date) AS max_date FROM campaigns
   ),
   periods AS (
       SELECT
           c.*,
           CASE
               WHEN Date >= max_date - INTERVAL 2 MONTH
                    THEN 'last_period'
               WHEN Date >= max_date - INTERVAL 4 MONTH
                AND Date <  max_date - INTERVAL 2 MONTH
                    THEN 'previous_period'
               ELSE 'other'
           END AS period
       FROM campaigns c
       CROSS JOIN bounds
   )
   SELECT period, ...
   FROM periods
   WHERE period IN ('last_period', 'previous_period')
   GROUP BY period;

- Calculate metrics separately for each period
- Use CTEs or subqueries for clarity

MULTI-DIMENSIONAL ANALYSIS:

- Channel analysis: GROUP BY Platform or Channel
- Funnel analysis: Calculate conversion rates between stages
- Segment analysis: GROUP BY demographic/audience columns
- Creative analysis: GROUP BY creative_variant, ad_copy, subject_line columns
- Time analysis: GROUP BY hour, day_of_week, or use DATE_TRUNC

PERFORMANCE ANALYSIS - CRITICAL:

When user asks about "performance", "best performing", "top performing", or "sort by performance", you MUST include ALL applicable KPIs:

* Raw Metrics (ALWAYS include):
  - Total_Spend = SUM("Total Spent")
  - Total_Impressions = SUM(Impressions)
  - Total_Clicks = SUM(Clicks)
  - Total_Conversions = SUM("Site Visit") or SUM(Conversions) [if exists]

* Calculated KPIs (ALWAYS include all applicable):
  - CTR (Click-Through Rate) = ROUND((SUM(Clicks) / NULLIF(SUM(Impressions), 0)) * 100, 2)
  - CPC (Cost Per Click) = ROUND(SUM("Total Spent") / NULLIF(SUM(Clicks), 0), 2)
  - CPM (Cost Per Mille) = ROUND((SUM("Total Spent") / NULLIF(SUM(Impressions), 0)) * 1000, 2)
  - CPA (Cost Per Acquisition) = ROUND(SUM("Total Spent") / NULLIF(SUM("Site Visit"), 0), 2) [if conversions exist]
  - Conversion_Rate = ROUND((SUM("Site Visit") / NULLIF(SUM(Clicks), 0)) * 100, 2) [if conversions exist]
  - ROAS (Return on Ad Spend) = ROUND(SUM(Revenue) / NULLIF(SUM("Total Spent"), 0), 2) [if Revenue exists]

- ORDER BY: Use the most relevant metric (CTR, ROAS, Conversion_Rate, or CPA depending on context)

- NEVER return just the dimension name (Channel, Funnel, etc.) without metrics
- NEVER return only one calculated metric - include ALL applicable KPIs

Examples:
1. "which is the best performing channel" should include:
   - Channel
   - Total_Spend, Total_Impressions, Total_Clicks, Total_Conversions
   - CTR, CPC, CPM, CPA, Conversion_Rate, ROAS (if applicable)
   - ORDER BY Conversion_Rate DESC or ROAS DESC (most relevant for "best")
   - LIMIT 1 (if asking for single best)

2. "sort by funnel performance" should include:
   - Funnel
   - All raw metrics + all calculated KPIs
   - ORDER BY the most relevant metric

ADVANCED PATTERNS:

- ROI calculation: (SUM(Revenue) - SUM(Spend)) / NULLIF(SUM(Spend), 0)
- Budget variance: SUM(Actual_Spend) - SUM(Budgeted_Spend)
- Growth rate: ((current - previous) / NULLIF(previous, 0)) * 100
- Drop-off rate: (stage1_count - stage2_count) / NULLIF(stage1_count, 0) * 100

EFFICIENCY & WASTE ANALYSIS - CRITICAL:

When user asks about "wasting money", "inefficient", "underperforming", "poor performance", or "worst campaigns":
- DO NOT use absolute thresholds like "conversions < 100" that may not match the data
- INSTEAD, use relative rankings to find the WORST performers compared to other campaigns
- ORDER BY the inefficiency metric (e.g., CPA DESC, ROAS ASC, Conversion_Rate ASC)
- Use LIMIT to show top N worst performers

Examples:
1. "Where am I wasting money?" should:
   - Calculate CPA, ROAS, Conversion_Rate for all campaigns
   - ORDER BY CPA DESC (highest cost per acquisition = most wasteful)
   - LIMIT 10 to show top 10 worst performers
   - NO absolute HAVING filter - just rank by inefficiency

2. "Which campaigns are underperforming?" should:
   - Calculate all efficiency metrics
   - ORDER BY Conversion_Rate ASC or ROAS ASC
   - LIMIT 10

3. "Show inefficient spend" should:
   - GROUP BY Campaign or Channel
   - ORDER BY CPA DESC or ROAS ASC
   - Include spend amount to show waste magnitude

SQL BEST PRACTICES:

- Use NULLIF to prevent division by zero
- Cast Date columns: CAST(Date AS DATE) or TRY_CAST(Date AS DATE)
- Use CTEs for complex multi-step queries
- Round decimals appropriately: ROUND(value, 2)
- Use descriptive column aliases
- For percentages, multiply by 100
- Column names are case-sensitive
- IMPORTANT: If column names contain underscores (e.g., Ad_Type, Device_Type), use them AS-IS without quotes
- If a column name is a SQL keyword (Type, Order, Group), wrap it in double quotes: "Type"
- Always reference columns exactly as they appear in the schema

ADVANCED ANALYTICAL PATTERNS:

**Anomaly Detection:**
- Use STDDEV() and AVG() to identify outliers: WHERE metric > AVG(metric) + 2*STDDEV(metric)
- Window functions for moving averages: AVG(metric) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
- Percent change from baseline: ((current - baseline) / NULLIF(baseline, 0)) * 100

**Cohort Analysis:**
- Use DATE_TRUNC to group by acquisition period
- Self-joins or window functions to compare cohorts
- Retention analysis: COUNT(DISTINCT user_id) by time period

**Trend Analysis:**
- Linear regression slope: REGR_SLOPE(y, x) for trend direction
- Moving averages: AVG(metric) OVER (ORDER BY date ROWS BETWEEN n PRECEDING AND CURRENT ROW)
- Growth rate: ((current - previous) / NULLIF(previous, 0)) * 100
- Cumulative metrics: SUM(metric) OVER (ORDER BY date)

**Statistical Analysis:**
- Standard deviation: STDDEV(metric) for volatility
- Variance: VARIANCE(metric)
- Percentiles: PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY metric) for median
- Correlation: CORR(metric1, metric2)

**Efficiency Analysis:**
- Pareto analysis: Use window functions with PERCENT_RANK() or cumulative sums
- Efficiency frontier: Rank by multiple criteria (volume AND efficiency)
- Marginal analysis: Compare incremental performance at different levels

**Segmentation:**
- CASE WHEN for bucketing (high/medium/low performers)
- NTILE(n) for equal-sized segments
- Clustering by multiple dimensions

**Forecasting Patterns:**
- Historical averages with trend adjustment
- Seasonality detection: GROUP BY DAYOFWEEK(Date) or MONTH(Date)
- Extrapolation: Use historical growth rates to project forward

**Multi-Touch Attribution:**
- Use ARRAY_AGG or STRING_AGG to track journey paths
- Window functions to identify first/last touch: FIRST_VALUE(), LAST_VALUE()
- Count touchpoints: COUNT(*) OVER (PARTITION BY user_id)

**Strategic Insights:**
- Scenario analysis: Use CASE WHEN to model different budget levels
- Optimization: Identify top performers with RANK() or ROW_NUMBER()
- Risk analysis: Calculate concentration with cumulative percentages

CRITICAL: DuckDB SQL Specifics:
- Use DATE_TRUNC('week/month/year', col) for grouping by time.
- Use col >= max_date - INTERVAL '14 days' for recent windows.
- Column names with spaces MUST be in double quotes (e.g., "Site Visit").
- If a column is a reserved word (e.g., Date), use double quotes: "Date".
- Always use NULLIF(denominator, 0) to prevent division by zero errors.

FEW-SHOT EXAMPLES:

Question: "How did CTR change week over week in the last 2 months?"
SQL: 
WITH bounds AS (SELECT MAX("Date") as max_date FROM campaigns),
weekly_stats AS (
    SELECT 
        DATE_TRUNC('week', "Date") as week,
        (SUM(Clicks) / NULLIF(SUM(Impressions), 0)) * 100 as ctr
    FROM campaigns, bounds
    WHERE "Date" >= max_date - INTERVAL '2 months'
    GROUP BY week
)
SELECT week, ctr, LAG(ctr) OVER (ORDER BY week) as prev_ctr
FROM weekly_stats ORDER BY week;

Question: "Which channel is most profitable based on ROAS?"
SQL:
SELECT Platform, 
    ROUND(SUM(Revenue) / NULLIF(SUM(Spend), 0), 2) as roas
FROM campaigns
GROUP BY Platform
HAVING SUM(Spend) > 0
ORDER BY roas DESC LIMIT 1;

CRITICAL VALUE MATCHING RULE:
When filtering by categorical columns (platform, channel, funnel, ad_type, device_type, campaign_name):
- You MUST use ONLY the EXACT values listed in the "IMPORTANT - Actual values in data" section above
- If the user mentions "Google Ads" but the data has "google_ads" or "Google Display Network", use the ACTUAL value from the schema
- If you cannot find a matching value, suggest similar values from the list
- NEVER guess or invent platform/channel names - only use values explicitly shown in the schema
- Platform names are case-sensitive and must match exactly

Question: {question}

SQL Query:""" # nosec B608
        
        logger.info(f"FULL PROMPT LENGTH: {len(prompt)} chars")
        logger.info(f"PROMPT PREVIEW (first 500 chars):\n{prompt[:500]}")
        logger.info(f"PROMPT END (last 200 chars):\n{prompt[-200:]}")
        
        # Try each available model in order
        sql_query = None
        last_error = None
        
        for provider, model_name in self.available_models:
            try:
                logger.info(f"Attempting to use {provider} ({model_name})...")
                
                if provider == 'claude':
                    response = self.anthropic_client.messages.create(
                        model=model_name,
                        max_tokens=2000,
                        temperature=0.1,
                        messages=[{
                            "role": "user",
                            "content": f"You are a SQL expert. Generate ONLY the SQL query, no explanations or markdown.\n\n{prompt}"
                        }]
                    )
                    sql_query = response.content[0].text.strip()
                    
                    if not sql_query or len(sql_query) < 10 or sql_query.strip().upper().endswith("FROM"):
                        logger.warning(f"{provider} returned truncated/empty SQL. Retrying next provider...")
                        continue
                        
                    self._last_model_used = f"{provider} ({model_name})"
                    logger.info(f"Successfully used {provider}")
                    break
                    
                elif provider == 'gemini':
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(
                        f"You are a SQL expert. Generate ONLY the SQL query, no explanations or markdown.\n\n{prompt}",
                        generation_config=genai.GenerationConfig(
                            temperature=0.1,
                            max_output_tokens=2500
                        )
                    )
                    sql_query = response.text.strip()
                    
                    if not sql_query or len(sql_query) < 10 or sql_query.strip().upper().endswith("FROM"):
                        logger.warning(f"{provider} returned truncated/empty SQL. Retrying next provider...")
                        continue

                    self._last_model_used = f"{provider} ({model_name})"
                    logger.info(f"Successfully used {provider} (FREE)")
                    break
                    
                elif provider == 'openai':
                    response = self.openai_client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": "You are a SQL expert. Generate ONLY the SQL query, no explanations or markdown."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,
                        max_tokens=2000
                    )
                    sql_query = response.choices[0].message.content.strip()
                    
                    if not sql_query or len(sql_query) < 10 or sql_query.strip().upper().endswith("FROM"):
                        logger.warning(f"{provider} returned truncated/empty SQL. Retrying next provider...")
                        continue

                    self._last_model_used = f"{provider} ({model_name})"
                    logger.info(f"Successfully used {provider}")
                    break
                    
                elif provider == 'groq':
                    response = self.groq_client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": "You are a SQL expert. Generate ONLY the SQL query, no explanations or markdown."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,
                        max_tokens=2000
                    )
                    sql_query = response.choices[0].message.content.strip()
                    
                    if not sql_query or len(sql_query) < 10 or sql_query.strip().upper().endswith("FROM"):
                        logger.warning(f"{provider} returned truncated/empty SQL. Retrying next provider...")
                        continue

                    self._last_model_used = f"{provider} ({model_name})"
                    logger.info(f"Successfully used {provider} (FREE & FAST)")
                    break
                    
                elif provider == 'deepseek':
                    response = self.deepseek_client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": "You are a SQL expert. Generate ONLY the SQL query, no explanations or markdown."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,
                        max_tokens=2000
                    )
                    sql_query = response.choices[0].message.content.strip()
                    
                    # Validate basic completion before accepting
                    if not sql_query or len(sql_query) < 10 or sql_query.strip().upper().endswith("FROM"):
                        logger.warning(f"{provider} returned truncated/empty SQL. Retrying next provider...")
                        continue

                    self._last_model_used = f"{provider} ({model_name})"
                    logger.info(f"Successfully used {provider} (FREE CODING SPECIALIST)")
                    break
                    
            except Exception as e:
                last_error = e
                logger.warning(f"{provider} failed: {e}")
                continue
        
        if not sql_query:
            logger.error(f"All models failed. Last error: {last_error}")
            raise Exception(f"All LLM providers failed. Last error: {last_error}")
        logger.info(f"RAW LLM RESPONSE: {sql_query}")
        
        # Clean up the query (remove markdown code blocks if present)
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        logger.info(f"AFTER CLEANUP: {sql_query}")
        
        # Sanitize SQL query to fix common issues
        sql_query = self._sanitize_sql(sql_query)
        logger.info(f"AFTER SANITIZE: {sql_query}")
        
        # ====================================================================================
        # MARKETING ANALYTICS VALIDATION PROTOCOL
        # Check for common mistakes and attempt self-correction
        # ====================================================================================
        validation_result = self._validate_marketing_sql_rules(sql_query)
        if not validation_result['all_passed']:
            logger.warning(f"SQL validation failed: {validation_result['failed_rules']}")
            
            # Attempt self-correction
            corrected_sql = self._self_correct_sql(sql_query, validation_result['failed_rules'], question)
            if corrected_sql:
                sql_query = corrected_sql
                logger.info(f"AFTER SELF-CORRECTION: {sql_query}")
            else:
                logger.warning("Self-correction failed, using original SQL with warnings")
        
        # Validate SQL completeness (detect truncated responses)
        sql_upper = sql_query.upper()
        open_parens = sql_query.count('(')
        close_parens = sql_query.count(')')
        
        is_incomplete = (
            ('SELECT' in sql_upper and 'FROM' not in sql_upper) or
            open_parens != close_parens or
            sql_query.rstrip().endswith(',') or
            sql_query.rstrip().endswith('(')
        )
        
        if is_incomplete:
            logger.warning(f"Detected incomplete/truncated SQL from LLM: {sql_query[:200]}...")
            raise ValueError(f"LLM returned incomplete SQL (truncated response). Triggering fallback.")
        
        # Validate SQL is not a dummy query
        if sql_query.upper().strip() == "SELECT 1" or not sql_query or len(sql_query) < 10:
            logger.error(f"LLM returned invalid/dummy query: '{sql_query}'")
            logger.error(f"Question was: {question}")
            logger.error(f"Schema had {len(self.schema_info.get('columns', []))} columns")
            raise ValueError(f"Failed to generate valid SQL for question: {question}. Got: {sql_query}")
        
        return sql_query
    
    def _validate_marketing_sql_rules(self, sql: str) -> Dict[str, Any]:
        """
        Validate SQL against marketing analytics best practices.
        
        Checks for:
        1. No AVG() on rate columns (CTR, ROAS, CPA, etc.)
        2. NULLIF usage for all divisions
        3. MAX(date) usage instead of CURRENT_DATE
        4. No arbitrary thresholds for ROAS/CPA
        
        Returns:
            Dict with 'all_passed', 'failed_rules', 'passed_rules'
        """
        import re
        sql_upper = sql.upper()
        
        checks = {
            'no_avg_on_rates': True,
            'has_nullif_for_division': True,
            'no_current_date': True,
            'no_arbitrary_thresholds': True
        }
        
        failed_rules = []
        
        # Rule 1: Check for AVG() on rate columns
        rate_columns = ['CTR', 'ROAS', 'CPA', 'CPC', 'CPM', 'CVR', 'CONVERSION_RATE']
        for col in rate_columns:
            if f'AVG({col})' in sql_upper or f'AVG( {col}' in sql_upper:
                checks['no_avg_on_rates'] = False
                failed_rules.append(f"Rule 1: Found AVG({col}) - use SUM(numerator)/NULLIF(SUM(denominator), 0) instead")
                break
        
        # Rule 2: Check for division without NULLIF
        # Look for patterns like "spend/conversions" without NULLIF
        division_pattern = r'/\s*(?!NULLIF)[a-zA-Z_]+\s*[,\n\)]'
        if re.search(division_pattern, sql_upper):
            # More specific check - find actual divisions
            if '/' in sql and 'NULLIF' not in sql_upper:
                checks['has_nullif_for_division'] = False
                failed_rules.append("Rule 2: Division without NULLIF - wrap denominator in NULLIF(x, 0)")
        
        # Rule 3: Check for CURRENT_DATE or NOW()
        if 'CURRENT_DATE' in sql_upper or 'NOW()' in sql_upper or 'GETDATE()' in sql_upper:
            checks['no_current_date'] = False
            failed_rules.append("Rule 3: Using CURRENT_DATE - use (SELECT MAX(date) FROM table) instead")
        
        # Rule 4: Check for arbitrary thresholds on ROAS/CPA
        # Look for patterns like "ROAS > 3" or "CPA < 50"
        threshold_pattern = r'(ROAS|CPA)\s*[><]=?\s*\d+'
        if re.search(threshold_pattern, sql_upper):
            checks['no_arbitrary_thresholds'] = False
            failed_rules.append("Rule 4: Arbitrary threshold - use ORDER BY and LIMIT or percentiles instead")
        
        all_passed = all(checks.values())
        passed_rules = [k for k, v in checks.items() if v]
        
        return {
            'all_passed': all_passed,
            'failed_rules': failed_rules,
            'passed_rules': passed_rules,
            'checks': checks
        }
    
    def _self_correct_sql(self, sql: str, failed_rules: List[str], question: str) -> Optional[str]:
        """
        Attempt to self-correct SQL that violates marketing analytics rules.
        
        Uses the LLM to rewrite the SQL fixing the identified issues.
        
        Args:
            sql: Original SQL query
            failed_rules: List of rule violations
            question: Original question for context
            
        Returns:
            Corrected SQL or None if correction fails
        """
        try:
            correction_prompt = f"""Your SQL query has the following marketing analytics rule violations:

{chr(10).join('- ' + rule for rule in failed_rules)}

Original Question: {question}

Original SQL:
{sql}

CRITICAL FIXES REQUIRED:
1. If using AVG(CTR) or AVG(ROAS) -> Change to SUM(clicks)*100.0/NULLIF(SUM(impressions),0) or SUM(revenue)/NULLIF(SUM(spend),0)
2. If division without NULLIF -> Wrap denominator: x/y becomes x/NULLIF(y, 0)
3. If using CURRENT_DATE -> Replace with (SELECT MAX(date) FROM campaigns)
4. If using arbitrary threshold like ROAS > 3 -> Use ORDER BY ROAS DESC LIMIT 10 instead

Rewrite the SQL to fix these issues while preserving the query intent.
Return ONLY the corrected SQL, no explanations."""

            # Use first available model for correction
            for provider, model_name in self.available_models:
                try:
                    if provider == 'claude':
                        response = self.anthropic_client.messages.create(
                            model=model_name,
                            max_tokens=1500,
                            temperature=0.1,
                            messages=[{
                                "role": "user",
                                "content": correction_prompt
                            }]
                        )
                        corrected = response.content[0].text.strip()
                    elif provider == 'gemini':
                        model = genai.GenerativeModel(model_name)
                        response = model.generate_content(
                            correction_prompt,
                            generation_config=genai.GenerationConfig(
                                temperature=0.1,
                                max_output_tokens=1500
                            )
                        )
                        corrected = response.text.strip()
                    elif provider == 'openai':
                        response = self.openai_client.chat.completions.create(
                            model=model_name,
                            messages=[
                                {"role": "system", "content": "You are a SQL correction expert. Fix the SQL query to follow marketing analytics best practices."},
                                {"role": "user", "content": correction_prompt}
                            ],
                            temperature=0.1,
                            max_tokens=1500
                        )
                        corrected = response.choices[0].message.content.strip()
                    elif provider == 'groq':
                        response = self.groq_client.chat.completions.create(
                            model=model_name,
                            messages=[
                                {"role": "system", "content": "You are a SQL correction expert. Fix the SQL query to follow marketing analytics best practices."},
                                {"role": "user", "content": correction_prompt}
                            ],
                            temperature=0.1,
                            max_tokens=1500
                        )
                        corrected = response.choices[0].message.content.strip()
                    elif provider == 'deepseek':
                        response = self.deepseek_client.chat.completions.create(
                            model=model_name,
                            messages=[
                                {"role": "system", "content": "You are a SQL correction expert. Fix the SQL query to follow marketing analytics best practices."},
                                {"role": "user", "content": correction_prompt}
                            ],
                            temperature=0.1,
                            max_tokens=1500
                        )
                        corrected = response.choices[0].message.content.strip()
                    else:
                        continue
                    
                    # Clean up the corrected SQL
                    corrected = corrected.replace("```sql", "").replace("```", "").strip()
                    
                    # Validate the correction fixed the issues
                    recheck = self._validate_marketing_sql_rules(corrected)
                    if recheck['all_passed']:
                        logger.info(f"Self-correction successful using {provider}")
                        return corrected
                    else:
                        logger.warning(f"Self-correction from {provider} still has issues: {recheck['failed_rules']}")
                        # Return corrected version anyway if it's better than original
                        if len(recheck['failed_rules']) < len(failed_rules):
                            return corrected
                        
                except Exception as e:
                    logger.warning(f"Self-correction failed with {provider}: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Self-correction failed: {e}")
            return None
    
    def _sanitize_sql(self, sql_query: str) -> str:
        """
        Sanitize SQL query to fix common issues.
        
        Args:
            sql_query: Original SQL query
            
        Returns:
            Sanitized SQL query
        """
        import re
        
        # Fix double-quoted identifiers that result from over-escaping
        # Pattern: ""identifier" or ""identifier".something"
        # This happens when LLM generates "Column.2" and we try to quote it again
        sql_query = re.sub(r'""([^"]+)"', r'"\1', sql_query)  # ""Campaign_Name" -> "Campaign_Name
        
        # Check if we need to use quoted column names (spaces in original data)
        # Look at the actual schema to determine the format
        if self.schema_info and 'columns' in self.schema_info:
            columns = self.schema_info['columns']
            
            # If columns have spaces, we need to quote them in SQL
            has_spaces = any(' ' in col for col in columns)
            
            if has_spaces:
                # Replace underscored versions with quoted space versions
                # But only if not already quoted
                patterns = [
                    (r'(?<!")Total_Spent(?!")', '"Total Spent"'),
                    (r'(?<!")Site_Visit(?!")', '"Site Visit"'),
                    (r'(?<!")Ad_Type(?!")', '"Ad Type"'),
                    (r'(?<!")Device_Type(?!")', '"Device Type"'),
                ]
            else:
                # Replace space versions with underscored versions
                patterns = [
                    (r'\bAd Type\b', 'Ad_Type'),
                    (r'\bDevice Type\b', 'Device_Type'),
                    (r'\bTotal Spent\b', 'Total_Spent'),
                    (r'\bSite Visit\b', 'Site_Visit'),
                ]
            
            for pattern, replacement in patterns:
                sql_query = re.sub(pattern, replacement, sql_query, flags=re.IGNORECASE)

            # If the schema has no Revenue column, replace any ROAS expression that
            # references SUM(Revenue) with a NULL placeholder to avoid binder errors.
            if 'Revenue' not in columns:
                sql_query = re.sub(
                    r'ROUND\s*\(\s*SUM\s*\(\s*Revenue\s*\)[^)]*\)\s+AS\s+ROAS',
                    'NULL AS ROAS',
                    sql_query,
                    flags=re.IGNORECASE,
                )
        
        return sql_query
    
    def execute_query(self, sql_query: str, analyze_plan: bool = False) -> pd.DataFrame:
        """
        Execute SQL query and return results.
        
        Args:
            sql_query: SQL query to execute
            analyze_plan: If True, analyze query plan with EXPLAIN
            
        Returns:
            DataFrame with query results
        """
        try:
            # --- STRICT VALIDATION (H2) ---
            if self.schema_info:
                allowed_tables = [self.schema_info.get("table_name", "campaigns")]
                # Add any views or multi-table manager tables
                if self.multi_table_manager:
                    allowed_tables.extend(list(self.multi_table_manager.tables.keys()))
                
                allowed_columns = self.schema_info.get("columns", [])
                
                SafeQueryExecutor.validate_query_against_schema(
                    sql_query,
                    allowed_tables=allowed_tables,
                    allowed_columns=allowed_columns
                )

            # Optionally analyze query plan
            if analyze_plan and self.optimizer:
                stats = self.optimizer.get_query_stats(sql_query)
                logger.info(f"Query Stats: {stats['execution_time']:.3f}s, Cost: {stats['cost']:.2f}")
                if stats['optimization_suggestions']:
                    logger.info("Optimization Suggestions:")
                    for suggestion in stats['optimization_suggestions']:
                        logger.info(f"  {suggestion}")
            
            result = self.conn.execute(sql_query).fetchdf()
            logger.info(f"Query executed successfully, returned {len(result)} rows")
            return result
        except duckdb.BinderException as be:
            logger.error(f"Binder Error (invalid column/table): {be}")
            raise ValueError(f"Invalid column or table in query: {be}")
        except duckdb.ParserException as pe:
            logger.error(f"SQL Syntax Error: {pe}")
            raise ValueError(f"SQL Syntax Error: {pe}")
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise
    
    def ask(self, question: str) -> Dict[str, Any]:
        """
        Ask a natural language question and get results.
        
        Args:
            question: Natural language question
        
        Returns:
            Dictionary with SQL query, results, and metadata
        """
        import time

        context_package: Optional[Dict[str, Any]] = None
        start_time = time.time()

        # --- BULLETPROOF QUERIES FIRST ---
        # For common query patterns, use pre-built, tested SQL templates
        # This bypasses LLM entirely for guaranteed reliability
        bulletproof_sql = BulletproofQueries.get_sql_for_question(question)
        if bulletproof_sql:
            logger.info(f"🎯 Using bulletproof template for: {question}")
            try:
                # Replace table name if needed
                table_name = self.get_table_name() if hasattr(self, 'get_table_name') else 'all_campaigns'
                sql_query = bulletproof_sql.replace('all_campaigns', table_name)
                
                # Execute the query
                with duckdb.connect() as conn:
                    if hasattr(self, 'parquet_path') and self.parquet_path:
                        conn.execute(f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM read_parquet('{self.parquet_path}')")
                    
                    results_df = conn.execute(sql_query).df()
                
                return {
                    "question": question,
                    "sql": sql_query.strip(),
                    "data": results_df.to_dict(orient="records"),
                    "row_count": len(results_df),
                    "execution_time": time.time() - start_time,
                    "source": "bulletproof_template",
                    "intents": BulletproofQueries.detect_intent(question)
                }
            except Exception as e:
                logger.warning(f"Bulletproof query failed: {e}. Falling back to LLM.")

        # --- TEMPLATE-FIRST APPROACH FOR STRUCTURED QUERIES ---
        # For queries that have well-defined templates (device, funnel, channel comparison),
        # try template matching FIRST before LLM generation for better reliability
        template_result = None
        if self.template_generator:
            try:
                all_templates = self.template_generator.generate_all_templates()
                q_lower = question.lower()
                
                # Check if user is requesting a specific dimension that might override template
                dimension_overrides = {
                    'by platform': 'platform',
                    'by channel': 'channel',
                    'by device': 'device',
                    'by funnel': 'funnel',
                    'per platform': 'platform',
                    'per channel': 'channel',
                    'each platform': 'platform',
                    'each channel': 'channel',
                }
                
                requested_dimension = None
                for phrase, dim in dimension_overrides.items():
                    if phrase in q_lower:
                        requested_dimension = dim
                        logger.info(f"Detected dimension override: '{phrase}' -> {dim}")
                        break
                
                # Check for template match
                for t_name, template in all_templates.items():
                    if any(pattern in q_lower for pattern in template.patterns):
                        # Skip template if user requested a dimension that the template doesn't provide
                        if requested_dimension:
                            # Templates that respect the dimension
                            dimension_aware_templates = ['device_performance', 'platform_comparison', 'channel_comparison']
                            if t_name not in dimension_aware_templates:
                                logger.info(f"Skipping template '{t_name}' - user requested '{requested_dimension}' dimension")
                                continue  # Skip this template and try LLM instead
                        
                        logger.info(f"Matched template FIRST: {template.name}")
                        sql_query = template.sql
                        
                        # Replace 'all_campaigns' with actual table name
                        if self.schema_info:
                            table_name = self.schema_info.get("table_name", "campaigns")
                            sql_query = sql_query.replace("all_campaigns", table_name)
                        
                        # Try executing the template query
                        try:
                            results = self.execute_query(sql_query)
                            
                            # Check if we got meaningful results
                            if not results.empty:
                                answer = self._generate_answer(question, results)
                                context_package = self.sql_helper.get_last_context_package() or {}
                                
                                return {
                                    "question": question,
                                    "sql_query": sql_query,
                                    "results": results,
                                    "answer": answer,
                                    "execution_time": time.time() - start_time,
                                    "model_used": f"Template: {template.name}",
                                    "sql_context": context_package,
                                    "success": True,
                                    "error": None
                                }
                            else:
                                # Template returned empty results, fall through to LLM
                                logger.info(f"Template {template.name} returned empty results, trying LLM...")
                                break
                        except Exception as template_exec_error:
                            # Template execution failed (e.g., column doesn't exist), fall through to LLM
                            logger.warning(f"Template execution failed: {template_exec_error}, trying LLM...")
                            break
            except Exception as template_error:
                logger.warning(f"Template matching failed: {template_error}, falling back to LLM...")

        # --- STANDARD LLM GENERATION ---
        try:
            # 1) Generate SQL with normal provider priority
            sql_query = self.generate_sql(question)

            # 2) Execute query
            results = self.execute_query(sql_query)

            context_package = self.sql_helper.get_last_context_package() or {}

            # 3) If no rows returned, optionally try a semantic fallback with DeepSeek
            if results.empty and any(m[0] == 'deepseek' for m in self.available_models):
                logger.warning(
                    "Primary model returned no rows. Attempting DeepSeek fallback for better SQL."
                )
                original_models = list(self.available_models)
                try:
                    # Prioritize DeepSeek for this retry only
                    deepseek_first = [m for m in original_models if m[0] == 'deepseek']
                    others = [m for m in original_models if m[0] != 'deepseek']
                    if deepseek_first:
                        self.available_models = deepseek_first + others
                        fallback_sql = self.generate_sql(question)
                        fallback_results = self.execute_query(fallback_sql)
                        if not fallback_results.empty:
                            logger.info("DeepSeek fallback produced non-empty results. Using fallback SQL.")
                            sql_query = fallback_sql
                            results = fallback_results
                            context_package = self.sql_helper.get_last_context_package() or context_package
                except Exception as fe:
                    logger.warning(f"DeepSeek semantic fallback failed: {fe}")
                finally:
                    # Restore original provider order for future calls
                    self.available_models = original_models

            # 4) Generate answer
            answer = self._generate_answer(question, results)

            execution_time = time.time() - start_time

            return {
                "question": question,
                "sql_query": sql_query,
                "results": results,
                "answer": answer,
                "execution_time": execution_time,
                "model_used": getattr(self, '_last_model_used', 'unknown'),
                "sql_context": context_package,
                "success": True,
                "error": None
            }

        except Exception as e:
            logger.warning(f"NL-to-SQL failed: {e}. Attempting template fallback...")
            
            # --- TEMPLATE FALLBACK ---
            if self.template_generator:
                try:
                    all_templates = self.template_generator.generate_all_templates()
                    best_template = None
                    
                    # Simple pattern matching for templates
                    q_lower = question.lower()
                    for t_name, template in all_templates.items():
                        if any(pattern in q_lower for pattern in template.patterns):
                            best_template = template
                            break
                    
                    if best_template:
                        logger.info(f"Matched template: {best_template.name}")
                        sql_query = best_template.sql
                        # Replace 'all_campaigns' if needed (DuckDB view or table name)
                        if self.schema_info:
                            table_name = self.schema_info.get("table_name", "campaigns")
                            sql_query = sql_query.replace("all_campaigns", table_name)
                        
                        results = self.execute_query(sql_query)
                        answer = self._generate_answer(question, results)
                        
                        return {
                            "question": question,
                            "sql_query": sql_query,
                            "results": results,
                            "answer": answer + "\n\n(Note: This answer was generated using a pre-defined analytical template as a fallback.)",
                            "execution_time": time.time() - start_time,
                            "model_used": "TemplateFallback",
                            "sql_context": context_package if 'context_package' in locals() else {},
                            "success": True,
                            "error": None
                        }
                except Exception as template_error:
                    logger.error(f"Template fallback also failed: {template_error}")

            return {
                "question": question,
                "sql_query": None,
                "results": None,
                "answer": None,
                "sql_context": context_package if 'context_package' in locals() else self.sql_helper.get_last_context_package(),
                "success": False,
                "error": str(e)
            }

    def _extract_sample_context(self, results: pd.DataFrame) -> str:
        """
        Extract sample size and confidence context from query results.
        
        Looks for conversion/sample size columns and provides confidence indicators.
        
        Args:
            results: Query results DataFrame
            
        Returns:
            String describing sample size and confidence level
        """
        if results.empty:
            return "No data available"
        
        context_parts = []
        
        # Number of rows
        row_count = len(results)
        context_parts.append(f"Rows: {row_count}")
        
        # Look for conversion/sample size columns
        conversion_cols = [c for c in results.columns if any(kw in c.lower() for kw in 
            ['conversion', 'sample', 'count', 'total_conversions', 'conversions', 'site_visit'])]
        
        total_conversions = 0
        for col in conversion_cols:
            try:
                col_sum = results[col].sum()
                if pd.notna(col_sum) and col_sum > 0:
                    total_conversions += col_sum
                    break  # Use first valid conversion column
            except:
                pass
        
        # Look for spend columns to understand scale
        spend_cols = [c for c in results.columns if any(kw in c.lower() for kw in 
            ['spend', 'cost', 'total_spent', 'budget'])]
        
        total_spend = 0
        for col in spend_cols:
            try:
                # Handle formatted strings like "$5.0K"
                if results[col].dtype == object:
                    # Try to extract numeric values
                    for val in results[col]:
                        if isinstance(val, str) and '$' in val:
                            # Parse $5.0K format
                            clean = val.replace('$', '').replace(',', '')
                            if 'K' in clean:
                                total_spend += float(clean.replace('K', '')) * 1000
                            elif 'M' in clean:
                                total_spend += float(clean.replace('M', '')) * 1000000
                            else:
                                total_spend += float(clean)
                        elif isinstance(val, (int, float)):
                            total_spend += val
                else:
                    total_spend = results[col].sum()
                break  # Use first valid spend column
            except:
                pass
        
        # Determine confidence level based on conversions
        if total_conversions > 0:
            context_parts.append(f"Total Conversions: {int(total_conversions):,}")
            
            if total_conversions >= 1000:
                confidence = "HIGH (>1000 conversions - statistically robust)"
            elif total_conversions >= 100:
                confidence = "MEDIUM (100-1000 conversions - directionally reliable)"
            else:
                confidence = "LOW (<100 conversions - interpret with caution)"
            
            context_parts.append(f"Confidence: {confidence}")
        elif row_count > 0:
            # No conversion column found, use row count
            if row_count >= 100:
                context_parts.append("Confidence: MEDIUM (based on row count)")
            else:
                context_parts.append("Confidence: LOW (limited data points)")
        
        if total_spend > 0:
            if total_spend >= 1000000:
                context_parts.append(f"Total Spend: ${total_spend/1000000:.1f}M")
            elif total_spend >= 1000:
                context_parts.append(f"Total Spend: ${total_spend/1000:.1f}K")
            else:
                context_parts.append(f"Total Spend: ${total_spend:.0f}")
        
        return " | ".join(context_parts)
    
    def _generate_answer(self, question: str, results: pd.DataFrame) -> str:
        """
        Generate strategic insights and recommendations from query results.
        
        Args:
            question: Original question
            results: Query results
            
        Returns:
            Strategic analysis with insights and recommendations
        """
        if results.empty:
            return "No results found for your question."
        
        # Convert results to text summary
        results_text = results.to_string(index=False, max_rows=20)
        
        # Extract date context from the data if available
        date_context = ""
        if self.schema_info:
            # Check for date columns in results
            date_cols = [col for col in results.columns if any(kw in col.lower() for kw in ['date', 'week', 'month', 'year', 'period'])]
            if date_cols:
                for col in date_cols:
                    try:
                        dates = pd.to_datetime(results[col], errors='coerce').dropna()
                        if not dates.empty:
                            min_date = dates.min()
                            max_date = dates.max()
                            date_context = f"\n\nDate Range in Results: {min_date.strftime('%B %Y')} to {max_date.strftime('%B %Y')}"
                            break
                    except Exception as e:
                        logger.debug(f"Failed to extract date from results: {e}")
            
            # If no date in results, check original data for context
            if not date_context and hasattr(self, 'conn') and self.conn:
                try:
                    # Get date range from original data
                    date_check = self.conn.execute("SELECT MIN(Date) as min_date, MAX(Date) as max_date FROM campaigns").fetchdf()
                    if not date_check.empty:
                        min_d = pd.to_datetime(date_check['min_date'].iloc[0])
                        max_d = pd.to_datetime(date_check['max_date'].iloc[0])
                        date_context = f"\n\nData covers: {min_d.strftime('%B %d, %Y')} to {max_d.strftime('%B %d, %Y')}"
                except Exception as e:
                    logger.debug(f"Failed to get date range from campaigns table: {e}")
        
        # Determine if this is an insight or recommendation question
        is_insight_question = any(keyword in question.lower() for keyword in [
            'why', 'what explains', 'root cause', 'underlying', 'story', 'pattern', 
            'hidden', 'surprising', 'counterintuitive', 'narrative', 'drivers'
        ])
        
        is_recommendation_question = any(keyword in question.lower() for keyword in [
            'recommend', 'should we', 'how should', 'what should', 'suggest', 
            'optimize', 'improve', 'action plan', 'strategy', 'roadmap'
        ])
        
        if is_recommendation_question:
            system_prompt = """You are a strategic marketing analyst providing actionable recommendations.

For RECOMMENDATIONS, you MUST:
* Be specific and actionable (not vague suggestions)
* Quantify expected impact where possible
* Consider implementation difficulty and timeline
* Assess risks and trade-offs
* Prioritize by potential business impact
* Provide clear success metrics

Format your recommendation as:
**Recommendation:** [Clear, specific action]
**Rationale:** [Data-driven evidence]
**Expected Impact:** [Quantified outcomes, e.g., "15-20% CPA reduction"]
**Implementation:** [How to execute, timeline]
**Risks:** [What could go wrong]
**Success Metrics:** [How to measure]
**Priority:** [High/Medium/Low]"""
            
            user_prompt = f"""Based on the data below, provide a strategic recommendation.

Question: {question}
{date_context}

Data:
{results_text}

IMPORTANT: If the question mentions a time period, explicitly state the specific dates/months/years in your response.

Provide a structured, actionable recommendation:"""
            max_tokens = 500
            
        elif is_insight_question:
            system_prompt = """You are a strategic marketing analyst uncovering deep insights.

For INSIGHTS, you MUST:
* Go beyond surface-level observations
* Connect multiple data points into coherent narratives
* Identify "so what" implications for business
* Distinguish correlation from causation
* Provide confidence levels for conclusions
* Explain the "why" behind patterns
* Compare against benchmarks when relevant

Provide insights that tell a story and reveal the underlying drivers of performance."""
            
            user_prompt = f"""Based on the data below, provide strategic insights that explain the underlying story.

Question: {question}
{date_context}

Data:
{results_text}

IMPORTANT: If the question mentions a time period (like "last month", "this week", etc.), explicitly state the specific dates/months/years the data covers in your response.

Provide deep insights with context and business implications:"""
            max_tokens = 400
            
        else:
            # ====================================================================================
            # ENHANCED 3-SECTION ANSWER FRAMEWORK (Phase 2)
            # Structure: Direct Answer → Context → Interpretation (conditional)
            # ====================================================================================
            
            # Calculate sample size context from results
            sample_size_info = self._extract_sample_context(results)
            
            system_prompt = """You are a marketing analytics expert (Rand Fishkin + Alex Freberg style).
You provide answers with DATA → CONTEXT → HYPOTHESIS → ACTION framework.

MANDATORY FORMAT - Always include these 3 sections:

**1. DIRECT ANSWER** (Required)
- Answer the literal question first
- Use actual numbers from the data
- Be specific: "Facebook has highest ROAS at 3.2x" not "Facebook performs well"
- One clear sentence if possible

**2. CONTEXT** (Required)
- How does this compare to averages/benchmarks?
- Sample size: How many conversions/rows support this conclusion?
- Confidence level: High (>1000 conversions), Medium (100-1000), Low (<100)
- Date range analyzed
- Any caveats or data quality notes

**3. INTERPRETATION** (Conditional - only if actionable)
IF results show anomalies, trends, or actionable patterns:
- WHY this might be happening (data-grounded hypotheses only)
- WHAT to investigate next
- SHOULD WE take action (with clear decision criteria)

IF results are straightforward:
- Skip this section or keep very brief

CRITICAL RULES:
- Never skip from DATA to ACTION without showing CONTEXT
- Always mention sample size / confidence
- Be specific with numbers, not vague
- Avoid speculation - only data-grounded hypotheses"""

            user_prompt = f"""Analyze this marketing data and provide a structured answer.

**Question:** {question}

**Date Context:** {date_context if date_context else "Not specified"}

**Sample Size Context:** {sample_size_info}

**Query Results:**
{results_text}

Provide your answer in the 3-section format (Direct Answer → Context → Interpretation):"""
            max_tokens = 450
        
        # Use same fallback system as SQL generation
        for provider, model_name in self.available_models:
            try:
                if provider == 'claude':
                    response = self.anthropic_client.messages.create(
                        model=model_name,
                        max_tokens=max_tokens,
                        temperature=0.7,
                        messages=[{
                            "role": "user",
                            "content": f"{system_prompt}\n\n{user_prompt}"
                        }]
                    )
                    return response.content[0].text.strip()
                    
                elif provider == 'gemini':
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(
                        f"{system_prompt}\n\n{user_prompt}",
                        generation_config=genai.GenerationConfig(
                            temperature=0.7,
                            max_output_tokens=max_tokens
                        )
                    )
                    return response.text.strip()
                    
                elif provider == 'openai':
                    response = self.openai_client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.7,
                        max_tokens=max_tokens
                    )
                    return response.choices[0].message.content.strip()
                    
                elif provider == 'groq':
                    response = self.groq_client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.7,
                        max_tokens=max_tokens
                    )
                    return response.choices[0].message.content.strip()
                    
                elif provider == 'deepseek':
                    response = self.deepseek_client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.7,
                        max_tokens=max_tokens
                    )
                    return response.choices[0].message.content.strip()
                    
            except Exception as e:
                logger.warning(f"Insights generation failed with {provider}: {e}")
                continue
        
        return "Unable to generate insights - all AI providers failed."
    
    def get_suggested_questions(self) -> List[str]:
        """Get suggested questions based on the data schema."""
        return [
            # Temporal Comparisons
            "Compare campaign performance between the last 2 weeks vs. the previous 2 weeks",
            "Show me the week-over-week trend for conversions over the last 2 months",
            "How did our CTR in the last month compare to the month before?",
            "What's the month-over-month growth in leads for the past 6 months?",
            "Compare Q3 2024 vs Q2 2024 performance for ROAS and CPA",
            
            # Channel & Performance Analysis
            "Which marketing channel generated the highest ROI?",
            "Compare the cost per acquisition (CPA) across different channels",
            "Which platform performs best in terms of ROAS? Calculate from total revenue and spend",
            "Show me the top 5 campaigns by conversions with their ROAS",
            
            # Funnel & Conversion Analysis
            "What was the conversion rate at each stage: impressions to clicks to conversions?",
            "Calculate the click-through rate and conversion rate for each platform",
            "Where did we see the highest drop-off in the funnel?",
            
            # Budget & ROI Analysis
            "Calculate the return on ad spend (ROAS) for each campaign",
            "What is the total spend vs total revenue across all campaigns?",
            "Which channel should we invest more in based on ROAS performance?",
            
            # Creative & Timing
            "What were the best performing days for campaign engagement?",
            "Show me performance trends by day of week",
            
            # Comparative Analysis
            "Compare new vs returning customer conversion metrics",
            "How did different audience segments perform in terms of engagement rate?"
        ]
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")


class QueryTemplates:
    """Pre-built query templates for common questions."""
    
    @staticmethod
    def get_templates() -> Dict[str, str]:
        """Get dictionary of query templates."""
        return {
            "top_campaigns_by_roas": """
                SELECT Campaign_Name, Platform, ROAS, Spend, Conversions
                FROM campaigns
                ORDER BY ROAS DESC
                LIMIT 10
            """,
            
            "total_spend_by_platform": """
                SELECT Platform, 
                       SUM(Spend) as Total_Spend,
                       SUM(Conversions) as Total_Conversions,
                       ROUND(SUM(Revenue) / NULLIF(SUM(Spend), 0), 2) as ROAS,
                       ROUND(SUM(Spend) / NULLIF(SUM(Conversions), 0), 2) as CPA
                FROM campaigns
                GROUP BY Platform
                ORDER BY Total_Spend DESC
            """,
            
            "campaign_performance_summary": """
                SELECT Campaign_Name,
                       COUNT(DISTINCT Platform) as Platforms,
                       SUM(Spend) as Total_Spend,
                       SUM(Conversions) as Total_Conversions,
                       ROUND(SUM(Revenue) / NULLIF(SUM(Spend), 0), 2) as ROAS,
                       ROUND(SUM(Spend) / NULLIF(SUM(Conversions), 0), 2) as CPA,
                       ROUND((SUM(Clicks) / NULLIF(SUM(Impressions), 0)) * 100, 2) as CTR
                FROM campaigns
                GROUP BY Campaign_Name
                ORDER BY Total_Spend DESC
            """,
            
            "monthly_trends": """
                SELECT DATE_TRUNC('month', CAST(Date AS DATE)) as Month,
                       SUM(Spend) as Total_Spend,
                       SUM(Conversions) as Total_Conversions,
                       ROUND(SUM(Revenue) / NULLIF(SUM(Spend), 0), 2) as ROAS,
                       ROUND(SUM(Spend) / NULLIF(SUM(Conversions), 0), 2) as CPA
                FROM campaigns
                GROUP BY Month
                ORDER BY Month
            """,
            
            "platform_comparison": """
                SELECT Platform,
                       COUNT(*) as Campaign_Count,
                       SUM(Impressions) as Total_Impressions,
                       SUM(Clicks) as Total_Clicks,
                       ROUND((SUM(Clicks) / NULLIF(SUM(Impressions), 0)) * 100, 2) as CTR,
                       ROUND(SUM(Spend) / NULLIF(SUM(Clicks), 0), 2) as CPC,
                       ROUND((SUM(Spend) / NULLIF(SUM(Impressions), 0)) * 1000, 2) as CPM,
                       SUM(Conversions) as Total_Conversions,
                       SUM(Spend) as Total_Spend,
                       ROUND(SUM(Spend) / NULLIF(SUM(Conversions), 0), 2) as CPA,
                       ROUND(SUM(Revenue) / NULLIF(SUM(Spend), 0), 2) as ROAS
                FROM campaigns
                GROUP BY Platform
                ORDER BY Total_Spend DESC
            """,
            
            "best_worst_performers": """
                (SELECT 'Top 5' as Category, Campaign_Name, Platform, ROAS, Spend
                 FROM campaigns
                 ORDER BY ROAS DESC
                 LIMIT 5)
                UNION ALL
                (SELECT 'Bottom 5' as Category, Campaign_Name, Platform, ROAS, Spend
                 FROM campaigns
                 ORDER BY ROAS ASC
                 LIMIT 5)
            """,
            
            "efficiency_analysis": """
                SELECT Campaign_Name,
                       Platform,
                       Spend,
                       Conversions,
                       CPA,
                       ROAS,
                       CASE 
                           WHEN ROAS >= 4.0 THEN 'Excellent'
                           WHEN ROAS >= 3.0 THEN 'Good'
                           WHEN ROAS >= 2.0 THEN 'Average'
                           ELSE 'Needs Improvement'
                       END as Performance_Category
                FROM campaigns
                ORDER BY ROAS DESC
            """
        }
