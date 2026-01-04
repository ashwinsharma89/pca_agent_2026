"""
Schema Manager for NL-to-SQL Query Engine

Handles schema information extraction, column detection, and unique values lookup.
This is the "ground truth" about what data is available for queries.

Pattern: Single Responsibility Principle
Depends on: DuckDB connection
Used by: NL-to-SQL Engine, Prompt Builder
"""

import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger


class SchemaManager:
    """
    Manages database schema information for the query engine.
    
    Responsibilities:
    - Extract schema from loaded data
    - Provide formatted schema for LLM context
    - Detect categorical columns and unique values
    - Map column aliases
    """
    
    def __init__(self, conn=None):
        """
        Initialize schema manager.
        
        Args:
            conn: DuckDB connection (optional, can be set later)
        """
        self.conn = conn
        self.schema_info: Dict[str, Any] = {}
        self.table_name = "campaigns"
    
    def set_connection(self, conn) -> None:
        """Set the database connection."""
        self.conn = conn
    
    def extract_schema(
        self, 
        df: pd.DataFrame, 
        table_name: str = "campaigns"
    ) -> Dict[str, Any]:
        """
        Extract schema information from a DataFrame.
        
        Args:
            df: pandas DataFrame
            table_name: Name of the table
        
        Returns:
            Dictionary with columns, dtypes, sample_data, etc.
        """
        self.table_name = table_name
        
        columns = list(df.columns)
        dtypes = {col: str(df[col].dtype) for col in columns}
        
        # Get sample rows for context
        sample_rows = []
        if len(df) > 0:
            sample = df.head(3)
            for _, row in sample.iterrows():
                sample_rows.append(dict(row))
        
        self.schema_info = {
            "table_name": table_name,
            "columns": columns,
            "dtypes": dtypes,
            "sample_data": sample_rows,
            "row_count": len(df)
        }
        
        return self.schema_info
    
    def get_schema_for_prompt(self) -> str:
        """
        Get formatted schema description for LLM prompt injection.
        
        Returns:
            Formatted string describing the schema
        """
        if not self.schema_info:
            raise ValueError(
                "Schema information not available. Call extract_schema() first."
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
        
        # Include unique values for categorical columns
        unique_values = self._get_categorical_unique_values(columns)
        if unique_values:
            lines.append("\nIMPORTANT - Actual values in data (use these EXACTLY for filters):")
            for col, values in unique_values.items():
                lines.append(f"  {col}: {values}")
        
        if sample_rows:
            lines.append("\nSample rows:")
            for row in sample_rows[:3]:
                lines.append(f"- {row}")
        
        return "\n".join(lines)
    
    def _get_categorical_unique_values(
        self, 
        columns: List[str],
        limit: int = 10
    ) -> Dict[str, List[str]]:
        """
        Get unique values for categorical columns.
        
        Args:
            columns: List of column names
            limit: Max unique values per column
        
        Returns:
            Dictionary mapping column name to unique values
        """
        if not self.conn:
            return {}
        
        unique_values = {}
        
        # Columns likely to be categorical
        categorical_patterns = [
            'platform', 'channel', 'funnel', 'ad_type', 'device_type', 
            'campaign_name', 'objective', 'placement', 'region', 'country'
        ]
        
        try:
            from .safe_query import SafeQueryExecutor
            table_name = self.schema_info.get("table_name", "campaigns")
            safe_table = SafeQueryExecutor.sanitize_identifier(table_name)
            
            for col in columns:
                col_lower = col.lower().replace(' ', '_')
                if any(pattern in col_lower for pattern in categorical_patterns):
                    try:
                        # Handle column names with spaces
                        if ' ' in col:
                            query = f'SELECT DISTINCT "{col}" FROM {safe_table} LIMIT {limit}'
                        else:
                            safe_col = SafeQueryExecutor.sanitize_identifier(col)
                            query = f'SELECT DISTINCT {safe_col} FROM {safe_table} LIMIT {limit}'
                        
                        result_df = self.conn.execute(query).fetchdf()
                        if not result_df.empty:
                            values = result_df.iloc[:, 0].dropna().tolist()
                            if values:
                                unique_values[col] = values
                    except Exception as e:
                        logger.debug(f"Could not get unique values for {col}: {e}")
        except Exception as e:
            logger.warning(f"Could not get categorical unique values: {e}")
        
        return unique_values
    
    def get_date_column(self) -> Optional[str]:
        """
        Detect the date column in the schema.
        
        Returns:
            Name of the date column, or None if not found
        """
        date_patterns = ['date', 'day', 'week', 'month', 'time', 'period']
        
        for col in self.schema_info.get("columns", []):
            col_lower = col.lower()
            if any(pattern in col_lower for pattern in date_patterns):
                return col
        
        return None
    
    def get_metric_columns(self) -> List[str]:
        """
        Detect metric columns (spend, impressions, clicks, etc.)
        
        Returns:
            List of metric column names
        """
        metric_patterns = [
            'spend', 'cost', 'impressions', 'clicks', 'conversions',
            'revenue', 'views', 'leads', 'purchases'
        ]
        
        metrics = []
        for col in self.schema_info.get("columns", []):
            col_lower = col.lower()
            if any(pattern in col_lower for pattern in metric_patterns):
                metrics.append(col)
        
        return metrics
    
    def get_dimension_columns(self) -> List[str]:
        """
        Detect dimension columns (platform, channel, etc.)
        
        Returns:
            List of dimension column names
        """
        dimension_patterns = [
            'platform', 'channel', 'campaign', 'funnel', 'device',
            'region', 'country', 'objective', 'placement', 'ad_type'
        ]
        
        dimensions = []
        for col in self.schema_info.get("columns", []):
            col_lower = col.lower().replace(' ', '_')
            if any(pattern in col_lower for pattern in dimension_patterns):
                dimensions.append(col)
        
        return dimensions
    
    def validate_column(self, column_name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if a column exists (case-insensitive matching).
        
        Args:
            column_name: Column name to validate
        
        Returns:
            Tuple of (exists, actual_column_name)
        """
        columns = self.schema_info.get("columns", [])
        
        # Exact match
        if column_name in columns:
            return (True, column_name)
        
        # Case-insensitive match
        for col in columns:
            if col.lower() == column_name.lower():
                return (True, col)
        
        return (False, None)


def get_schema_manager(conn=None) -> SchemaManager:
    """Get a schema manager instance."""
    return SchemaManager(conn)
