"""
Prompt Builder for NL-to-SQL Query Engine

Constructs the LLM prompt with schema, context, and SQL rules.
Separates prompt construction from the query engine for testability.

Pattern: Builder Pattern
Depends on: Schema Manager, Marketing Context, Hybrid Retrieval
Used by: NL-to-SQL Engine
"""

from typing import Dict, Any, List, Optional
from loguru import logger


# SQL Best Practices Template (condensed from the massive prompt)
SQL_RULES_TEMPLATE = """
CRITICAL AGGREGATION RULES - NEVER VIOLATE:

For calculated/rate metrics (CTR, CPC, CPM, CPA, ROAS), you MUST:
* ALWAYS compute from aggregates: SUM(numerator) / SUM(denominator)
- NEVER use AVG() on pre-calculated rate columns

Examples:
- CTR = (SUM(Clicks) / NULLIF(SUM(Impressions), 0)) * 100
- CPC = SUM(Spend) / NULLIF(SUM(Clicks), 0)
- CPM = (SUM(Spend) / NULLIF(SUM(Impressions), 0)) * 1000
- CPA = SUM(Spend) / NULLIF(SUM(Conversions), 0)
- ROAS = SUM(Revenue) / NULLIF(SUM(Spend), 0)
- Conversion_Rate = (SUM(Conversions) / NULLIF(SUM(Clicks), 0)) * 100

TEMPORAL PATTERNS (ANCHOR ON DATA, NOT CURRENT_DATE):

Always anchor relative time windows on the *latest date present in the data*.

1) Find the campaign end date first:
   WITH bounds AS (
       SELECT MAX([date_column]) AS max_date
       FROM campaigns
   )

2) Express time windows relative to bounds.max_date:
- "last 2 weeks"     -> [date] >= max_date - INTERVAL 14 DAY
- "last month"       -> [date] >= DATE_TRUNC('month', max_date - INTERVAL 1 MONTH)
- "week-over-week"   -> GROUP BY DATE_TRUNC('week', [date])

SQL BEST PRACTICES:

- Use NULLIF to prevent division by zero
- Cast Date columns: CAST(Date AS DATE) or TRY_CAST(Date AS DATE)
- Use CTEs for complex multi-step queries
- Round decimals appropriately: ROUND(value, 2)
- Use descriptive column aliases
- Column names are case-sensitive
- Column names with underscores (Ad_Type) use AS-IS without quotes
- SQL keywords as column names need quotes: "Type", "Order"

PERFORMANCE ANALYSIS:

When user asks about "performance", "best performing", "top", include ALL applicable KPIs:

* Raw Metrics:
  - Total_Spend = SUM("Total Spent")
  - Total_Impressions = SUM(Impressions)
  - Total_Clicks = SUM(Clicks)
  - Total_Conversions = SUM(Conversions)

* Calculated KPIs:
  - CTR, CPC, CPM, CPA, Conversion_Rate, ROAS

EFFICIENCY & WASTE ANALYSIS:

When user asks about "wasting money", "inefficient", "underperforming":
- DO NOT use absolute thresholds
- Use relative rankings: ORDER BY CPA DESC or ROAS ASC
- LIMIT to show top N worst performers
"""


class PromptBuilder:
    """
    Builds the LLM prompt for SQL generation.
    
    Responsibilities:
    - Combine schema, context, and rules
    - Inject query analysis hints
    - Format the final prompt for the LLM
    """
    
    def __init__(self):
        self.schema_description: str = ""
        self.marketing_context: str = ""
        self.sql_context: str = ""
        self.query_analysis: str = ""
    
    def set_schema(self, schema_description: str) -> "PromptBuilder":
        """Set the schema description."""
        self.schema_description = schema_description
        return self
    
    def set_marketing_context(self, context: str) -> "PromptBuilder":
        """Set the marketing domain context."""
        self.marketing_context = context
        return self
    
    def set_sql_context(self, context: str) -> "PromptBuilder":
        """Set the SQL knowledge context."""
        self.sql_context = context
        return self
    
    def set_query_analysis(
        self,
        intent: str,
        complexity: str,
        entities: Any,
    ) -> "PromptBuilder":
        """
        Set the query analysis from hybrid retrieval.
        
        Args:
            intent: Query intent (aggregation, comparison, etc.)
            complexity: Query complexity (simple, medium, complex)
            entities: Extracted entities (group_by, metrics, etc.)
        """
        sql_hints = []
        mandatory_instructions = []
        
        # Group by extraction
        if entities.group_by:
            sql_hints.append(f"GROUP BY: {', '.join(entities.group_by)}")
            group_by_mapping = {
                'platform': 'Platform',
                'channel': 'Channel',
                'device': '"Device Type"',
                'funnel': 'Funnel',
                'campaign': 'Campaign_Name_Full',
            }
            actual_cols = [group_by_mapping.get(g, g) for g in entities.group_by]
            mandatory_instructions.append(
                f"⚠️ MANDATORY: User said 'by {', '.join(entities.group_by)}' - "
                f"YOU MUST GROUP BY {', '.join(actual_cols)}"
            )
        
        # Granularity extraction
        if entities.granularity:
            granularity_sql = {
                'daily': "DATE_TRUNC('day', \"Date\") AS date",
                'weekly': "DATE_TRUNC('week', \"Date\") AS week_start",
                'monthly': "STRFTIME(\"Date\", 'Mon-YY') AS month",
            }
            sql_hints.append(f"GRANULARITY: {entities.granularity}")
            mandatory_instructions.append(
                f"⚠️ MANDATORY GRANULARITY: User asked for {entities.granularity.upper()} data.\n"
                f"Include in SELECT: {granularity_sql.get(entities.granularity, '')}\n"
                f"GROUP BY the date column with DATE_TRUNC\n"
                f"ORDER BY date chronologically"
            )
        
        if entities.metrics:
            sql_hints.append(f"METRICS: {', '.join(entities.metrics)}")
        if entities.time_period:
            sql_hints.append(f"TIME FILTER: {entities.time_period}")
        if entities.limit:
            sql_hints.append(f"LIMIT: {entities.limit}")
        if entities.order_by:
            sql_hints.append(f"ORDER: {entities.order_by}")
        
        self.query_analysis = f"""
⚠️ CRITICAL QUERY ANALYSIS - FOLLOW THESE INSTRUCTIONS:
- Intent: {intent.upper()}
- Complexity: {complexity.upper()}
- Required SQL patterns: {', '.join(sql_hints) if sql_hints else 'Standard aggregation'}
{chr(10).join(mandatory_instructions)}
"""
        return self
    
    def build(self, question: str) -> str:
        """
        Build the final prompt for the LLM.
        
        Args:
            question: Natural language question
        
        Returns:
            Complete prompt string
        """
        prompt = f"""You are a SQL expert specializing in marketing campaign analytics. Convert the following natural language question into a DuckDB SQL query.

{self.query_analysis}

{self.marketing_context}

Database Schema:
{self.schema_description}

SQL Knowledge & Reference:
{self.sql_context}

{SQL_RULES_TEMPLATE}

Question: {question}

IMPORTANT:
- Return ONLY the SQL query, no explanations
- Use the exact column names from the schema (case-sensitive)
- Apply all relevant aggregation rules

SQL Query:
"""
        return prompt
    
    def build_correction_prompt(
        self,
        original_sql: str,
        failed_rules: List[str],
        question: str
    ) -> str:
        """
        Build prompt for SQL self-correction.
        
        Args:
            original_sql: The SQL that failed validation
            failed_rules: List of rule violations
            question: Original question for context
        
        Returns:
            Correction prompt
        """
        return f"""The following SQL query violates marketing analytics best practices.

Original SQL:
{original_sql}

Violations:
{chr(10).join(f'- {rule}' for rule in failed_rules)}

Original Question: {question}

Please rewrite the SQL to fix these issues, following these rules:
1. Never use AVG() on rate columns (CTR, ROAS, etc.)
2. Always use NULLIF for divisions
3. Use MAX(date) from data instead of CURRENT_DATE
4. Avoid arbitrary thresholds for ROAS/CPA

Corrected SQL:
"""
    
    def build_answer_prompt(
        self,
        question: str,
        results_summary: str,
        sample_context: str = ""
    ) -> str:
        """
        Build prompt for generating strategic insights from results.
        
        Args:
            question: Original question
            results_summary: Summary of query results
            sample_context: Sample size and confidence context
        
        Returns:
            Answer generation prompt
        """
        return f"""You are a senior marketing analyst. Based on the following query results, provide strategic insights and actionable recommendations.

Question: {question}

{sample_context}

Results Summary:
{results_summary}

Provide:
1. Key findings (2-3 bullet points)
2. Strategic recommendations (2-3 actionable items)
3. Potential areas for further investigation

Keep the response concise and actionable.
"""


def get_prompt_builder() -> PromptBuilder:
    """Get a new prompt builder instance."""
    return PromptBuilder()
