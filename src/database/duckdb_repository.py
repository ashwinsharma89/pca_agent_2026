"""
DuckDB Repository (Data Access Layer)

Provides data access for campaign analytics using DuckDB + Parquet.
This is separate from SQL-based repositories to handle analytics workloads.

Pattern: Repository Pattern
Depends on: DuckDB Manager, Column Mapping
Used by: Campaign Service
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from loguru import logger

from src.database.duckdb_manager import get_duckdb_manager
from src.utils.column_mapping import find_column, METRIC_COLUMN_ALIASES


class DuckDBRepository:
    """
    Repository for DuckDB-based analytics operations.
    
    Provides:
    - Raw data retrieval
    - Aggregated metrics
    - Time series data
    - Schema information
    - Filter options
    """
    
    def __init__(self):
        self._manager = None
    
    @property
    def manager(self):
        """Lazy-load DuckDB manager."""
        if self._manager is None:
            self._manager = get_duckdb_manager()
        return self._manager
    
    # ========================================================================
    # RAW DATA RETRIEVAL
    # ========================================================================
    
    def get_campaigns_df(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        platforms: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Get campaign data as DataFrame with optional filters.
        
        Args:
            start_date: Filter start date (YYYY-MM-DD)
            end_date: Filter end date (YYYY-MM-DD)
            platforms: List of platforms to filter
            limit: Maximum rows to return
        
        Returns:
            pandas DataFrame with campaign data
        """
        with self.manager.connection() as conn:
            # Build query dynamically
            query = "SELECT * FROM campaigns WHERE 1=1"
            params = []
            
            if start_date:
                query += " AND \"Date\" >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND \"Date\" <= ?"
                params.append(end_date)
            
            if platforms:
                placeholders = ", ".join(["?" for _ in platforms])
                query += f" AND \"Platform\" IN ({placeholders})"
                params.extend(platforms)
            
            if limit:
                query += f" LIMIT {limit}"
            
            try:
                return conn.execute(query, params).df()
            except Exception as e:
                logger.error(f"Failed to get campaigns: {e}")
                return pd.DataFrame()
    
    # ========================================================================
    # AGGREGATED METRICS
    # ========================================================================
    
    def get_aggregated_metrics(
        self,
        group_by: str = "Platform",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        platforms: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Get aggregated metrics grouped by dimension.
        
        Args:
            group_by: Column to group by (e.g., "Platform", "Channel")
            start_date: Filter start date
            end_date: Filter end date
            platforms: List of platforms to filter
        
        Returns:
            DataFrame with aggregated metrics per group
        """
        with self.manager.connection() as conn:
            query = f"""
                SELECT 
                    "{group_by}" as dimension,
                    SUM(COALESCE("Spend", 0)) as spend,
                    SUM(COALESCE("Impressions", 0)) as impressions,
                    SUM(COALESCE("Clicks", 0)) as clicks,
                    SUM(COALESCE("Conversions", 0)) as conversions,
                    SUM(COALESCE("Revenue", 0)) as revenue,
                    COUNT(*) as row_count
                FROM campaigns
                WHERE 1=1
            """
            params = []
            
            if start_date:
                query += " AND \"Date\" >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND \"Date\" <= ?"
                params.append(end_date)
            
            if platforms:
                placeholders = ", ".join(["?" for _ in platforms])
                query += f" AND \"Platform\" IN ({placeholders})"
                params.extend(platforms)
            
            query += f' GROUP BY "{group_by}"'
            query += " ORDER BY spend DESC"
            
            try:
                return conn.execute(query, params).df()
            except Exception as e:
                logger.error(f"Failed to get aggregated metrics: {e}")
                return pd.DataFrame()
    
    def get_total_metrics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        platforms: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """
        Get total aggregated metrics (no grouping).
        
        Returns:
            Dictionary with total spend, impressions, clicks, conversions, revenue
        """
        with self.manager.connection() as conn:
            query = """
                SELECT 
                    SUM(COALESCE("Spend", 0)) as total_spend,
                    SUM(COALESCE("Impressions", 0)) as total_impressions,
                    SUM(COALESCE("Clicks", 0)) as total_clicks,
                    SUM(COALESCE("Conversions", 0)) as total_conversions,
                    SUM(COALESCE("Revenue", 0)) as total_revenue,
                    COUNT(*) as row_count
                FROM campaigns
                WHERE 1=1
            """
            params = []
            
            if start_date:
                query += " AND \"Date\" >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND \"Date\" <= ?"
                params.append(end_date)
            
            if platforms:
                placeholders = ", ".join(["?" for _ in platforms])
                query += f" AND \"Platform\" IN ({placeholders})"
                params.extend(platforms)
            
            try:
                result = conn.execute(query, params).fetchone()
                if result:
                    return {
                        "spend": float(result[0] or 0),
                        "impressions": int(result[1] or 0),
                        "clicks": int(result[2] or 0),
                        "conversions": int(result[3] or 0),
                        "revenue": float(result[4] or 0),
                        "row_count": int(result[5] or 0)
                    }
            except Exception as e:
                logger.error(f"Failed to get total metrics: {e}")
            
            return {"spend": 0, "impressions": 0, "clicks": 0, "conversions": 0, "revenue": 0, "row_count": 0}
    
    # ========================================================================
    # TIME SERIES
    # ========================================================================
    
    def get_time_series(
        self,
        metric: str = "spend",
        granularity: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        platforms: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Get time series data for a metric.
        
        Args:
            metric: Metric to aggregate (spend, clicks, etc.)
            granularity: daily, weekly, or monthly
            start_date: Filter start date
            end_date: Filter end date
            platforms: List of platforms to filter
        
        Returns:
            DataFrame with date and value columns
        """
        with self.manager.connection() as conn:
            # Determine date truncation
            if granularity == "monthly":
                date_expr = "DATE_TRUNC('month', \"Date\")"
            elif granularity == "weekly":
                date_expr = "DATE_TRUNC('week', \"Date\")"
            else:
                date_expr = "\"Date\""
            
            # Map metric to column
            metric_col = metric.capitalize()
            
            query = f"""
                SELECT 
                    {date_expr} as date,
                    SUM(COALESCE("{metric_col}", 0)) as value
                FROM campaigns
                WHERE 1=1 AND "Date" IS NOT NULL
            """
            params = []
            
            if start_date:
                query += " AND \"Date\" >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND \"Date\" <= ?"
                params.append(end_date)
            
            if platforms:
                placeholders = ", ".join(["?" for _ in platforms])
                query += f" AND \"Platform\" IN ({placeholders})"
                params.extend(platforms)
            
            query += f" GROUP BY {date_expr} ORDER BY date"
            
            try:
                return conn.execute(query, params).df()
            except Exception as e:
                logger.error(f"Failed to get time series: {e}")
                return pd.DataFrame()
    
    # ========================================================================
    # SCHEMA & METADATA
    # ========================================================================
    
    def get_schema_info(self) -> Dict[str, Any]:
        """
        Get schema metadata about available columns.
        
        Returns:
            Dictionary with columns, metrics, dimensions, and row count
        """
        with self.manager.connection() as conn:
            try:
                schema_df = conn.execute("DESCRIBE campaigns").df()
                columns = schema_df.to_dict('records')
                
                # Get sample to detect available columns
                sample = conn.execute("SELECT * FROM campaigns LIMIT 1").df()
                
                # Detect available metrics
                metrics_available = {}
                for metric_key in ['spend', 'impressions', 'clicks', 'conversions', 'revenue']:
                    col = find_column(sample, metric_key)
                    metrics_available[metric_key] = col is not None
                
                # Detect available dimensions
                dimensions_available = {}
                for dim_key in ['platform', 'channel', 'campaign', 'device', 'region', 'objective', 'funnel']:
                    col = find_column(sample, dim_key)
                    dimensions_available[dim_key] = col is not None
                
                # Get row count
                row_count = conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
                
                return {
                    "columns": columns,
                    "metrics": metrics_available,
                    "dimensions": dimensions_available,
                    "row_count": row_count
                }
            except Exception as e:
                logger.error(f"Failed to get schema: {e}")
                return {"columns": [], "metrics": {}, "dimensions": {}, "row_count": 0}
    
    def get_filter_options(self) -> Dict[str, List[str]]:
        """
        Get all unique filter option values for dropdowns.
        
        Returns:
            Dictionary mapping dimension -> list of unique values
        """
        with self.manager.connection() as conn:
            options = {}
            
            # Get sample to detect columns
            try:
                sample = conn.execute("SELECT * FROM campaigns LIMIT 1").df()
            except Exception:
                return options
            
            # Dimension columns to get options for
            dimensions = ['platform', 'channel', 'campaign', 'device', 'region', 
                         'objective', 'ad_type', 'funnel', 'placement']
            
            for dim in dimensions:
                col = find_column(sample, dim)
                if col:
                    try:
                        result = conn.execute(
                            f'SELECT DISTINCT "{col}" FROM campaigns WHERE "{col}" IS NOT NULL ORDER BY "{col}"'
                        ).fetchall()
                        options[dim] = [str(row[0]) for row in result if row[0]]
                    except Exception as e:
                        logger.warning(f"Could not get options for {dim}: {e}")
            
            return options
    
    def get_date_range(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Get the min and max dates from the data.
        
        Returns:
            Tuple of (min_date, max_date) as strings
        """
        with self.manager.connection() as conn:
            try:
                result = conn.execute(
                    'SELECT MIN("Date"), MAX("Date") FROM campaigns WHERE "Date" IS NOT NULL'
                ).fetchone()
                if result:
                    return (
                        str(result[0]) if result[0] else None, 
                        str(result[1]) if result[1] else None
                    )
            except Exception as e:
                logger.error(f"Failed to get date range: {e}")
            return (None, None)
    
    # ========================================================================
    # DATA MODIFICATION
    # ========================================================================
    
    def save_campaigns(self, df: pd.DataFrame) -> int:
        """
        Save campaign DataFrame to storage.
        
        Args:
            df: pandas DataFrame with campaign data
        
        Returns:
            Number of rows saved
        """
        return self.manager.save_campaigns(df)
    
    def execute_raw_query(self, query: str, params: Optional[List] = None) -> pd.DataFrame:
        """
        Execute a raw SQL query (for advanced use cases).
        
        Args:
            query: SQL query string
            params: Query parameters
        
        Returns:
            DataFrame with query results
        """
        with self.manager.connection() as conn:
            try:
                if params:
                    return conn.execute(query, params).df()
                return conn.execute(query).df()
            except Exception as e:
                logger.error(f"Query failed: {e}")
                return pd.DataFrame()


# Singleton instance
_repository: Optional[DuckDBRepository] = None


def get_duckdb_repository() -> DuckDBRepository:
    """Get the singleton DuckDB repository instance."""
    global _repository
    if _repository is None:
        _repository = DuckDBRepository()
    return _repository
