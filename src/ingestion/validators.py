"""
Data Validators (Layer 3)

Provides validation at two stages:
- Stage 1 (Fast): DuckDB CHECK constraints
- Stage 2 (Deep): Pandera DataFrame schema validation

Design Pattern: Chain of Responsibility
Input: Normalized DataFrame from Layer 2
Output: Validated DataFrame with quality report
"""

import pandas as pd
import pandera as pa
from pandera import Column, Check, DataFrameSchema
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
from enum import Enum


class ValidationSeverity(Enum):
    """Severity levels for validation errors."""
    ERROR = "error"      # Must fix, data rejected
    WARNING = "warning"  # Should fix, data accepted with flag
    INFO = "info"        # FYI, no action needed


class ValidationResult:
    """Container for validation results."""
    
    def __init__(self):
        self.passed: bool = True
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.row_count: int = 0
        self.valid_rows: int = 0
        self.invalid_rows: int = 0
    
    def add_error(self, column: str, message: str, count: int = 1):
        """Add a validation error."""
        self.passed = False
        self.errors.append({
            "column": column,
            "message": message,
            "count": count,
            "severity": ValidationSeverity.ERROR.value
        })
    
    def add_warning(self, column: str, message: str, count: int = 1):
        """Add a validation warning."""
        self.warnings.append({
            "column": column,
            "message": message,
            "count": count,
            "severity": ValidationSeverity.WARNING.value
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "passed": self.passed,
            "row_count": self.row_count,
            "valid_rows": self.valid_rows,
            "invalid_rows": self.invalid_rows,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings
        }


# ============================================================================
# PANDERA SCHEMA DEFINITIONS
# ============================================================================

CampaignSchema = pa.DataFrameSchema(
    {
        # Core metrics - must be non-negative
        "spend": Column(pa.Float, nullable=True, checks=[
            Check.ge(0, error="Spend must be >= 0"),
        ], coerce=True),
        
        "impressions": Column(pa.Int, nullable=True, checks=[
            Check.ge(0, error="Impressions must be >= 0"),
        ], coerce=True),
        
        "clicks": Column(pa.Int, nullable=True, checks=[
            Check.ge(0, error="Clicks must be >= 0"),
        ], coerce=True),
        
        "conversions": Column(pa.Int, nullable=True, checks=[
            Check.ge(0, error="Conversions must be >= 0"),
        ], coerce=True),
        
        "revenue": Column(pa.Float, nullable=True, checks=[
            Check.ge(0, error="Revenue must be >= 0"),
        ], coerce=True),
        
        # Dimensions
        "platform": Column(pa.String, nullable=True, coerce=True),
        "channel": Column(pa.String, nullable=True, coerce=True),
        "campaign": Column(pa.String, nullable=True, coerce=True),
        
        # Date - must be valid
        "date": Column(pa.DateTime, nullable=True, coerce=True),
    },
    strict=False,  # Allow extra columns
    coerce=True,   # Coerce types
    ordered=False  # Column order doesn't matter
)


# Extended schema with all optional fields
FullCampaignSchema = CampaignSchema.add_columns({
    "funnel": Column(pa.String, nullable=True, coerce=True),
    "device": Column(pa.String, nullable=True, coerce=True),
    "region": Column(pa.String, nullable=True, coerce=True),
    "objective": Column(pa.String, nullable=True, coerce=True),
    "ad_type": Column(pa.String, nullable=True, coerce=True),
})


class DataValidator:
    """
    Validates data quality using Pandera schemas.
    
    Features:
    - Fast constraint checking
    - Deep schema validation
    - Row-level error tracking
    - Configurable strictness
    """
    
    def __init__(
        self,
        schema: pa.DataFrameSchema = CampaignSchema,
        strict: bool = False,
        log_errors: bool = True
    ):
        """
        Initialize validator.
        
        Args:
            schema: Pandera schema to validate against
            strict: If True, reject DataFrame on any error
            log_errors: If True, log validation errors
        """
        self.schema = schema
        self.strict = strict
        self.log_errors = log_errors
    
    def validate(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, ValidationResult]:
        """
        Validate DataFrame against schema.
        
        Args:
            df: Input DataFrame
        
        Returns:
            Tuple of (validated DataFrame, ValidationResult)
        """
        result = ValidationResult()
        result.row_count = len(df)
        
        if df.empty:
            result.valid_rows = 0
            return df, result
        
        # Stage 1: Fast constraint checks
        df, stage1_result = self._fast_validate(df)
        result.errors.extend(stage1_result.errors)
        result.warnings.extend(stage1_result.warnings)
        
        # Stage 2: Pandera deep validation
        try:
            validated_df = self.schema.validate(df, lazy=True)
            result.valid_rows = len(validated_df)
            result.invalid_rows = result.row_count - result.valid_rows
            return validated_df, result
            
        except pa.errors.SchemaErrors as e:
            # Collect all validation errors
            for error in e.failure_cases.to_dict('records'):
                col = error.get('column', 'unknown')
                check = error.get('check', 'unknown')
                result.add_error(
                    column=col,
                    message=f"Failed check: {check}",
                    count=1
                )
            
            if self.log_errors:
                logger.warning(f"Validation errors: {len(result.errors)}")
            
            if self.strict:
                raise
            
            # Return original DataFrame with warnings
            result.valid_rows = len(df) - len(e.failure_cases)
            result.invalid_rows = len(e.failure_cases)
            result.passed = not self.strict
            
            return df, result
    
    def _fast_validate(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, ValidationResult]:
        """
        Fast validation using simple checks.
        
        This is Stage 1 - quick sanity checks before deep validation.
        """
        result = ValidationResult()
        df = df.copy()
        
        # Check 1: clicks <= impressions
        if 'clicks' in df.columns and 'impressions' in df.columns:
            invalid = (df['clicks'] > df['impressions']) & df['impressions'].notna()
            if invalid.any():
                count = invalid.sum()
                result.add_warning(
                    column='clicks',
                    message=f"Clicks exceed impressions ({count} rows)",
                    count=count
                )
                # Auto-fix: cap clicks at impressions
                df.loc[invalid, 'clicks'] = df.loc[invalid, 'impressions']
        
        # Check 2: conversions <= clicks
        if 'conversions' in df.columns and 'clicks' in df.columns:
            invalid = (df['conversions'] > df['clicks']) & df['clicks'].notna()
            if invalid.any():
                count = invalid.sum()
                result.add_warning(
                    column='conversions',
                    message=f"Conversions exceed clicks ({count} rows)",
                    count=count
                )
                # Auto-fix: cap conversions at clicks
                df.loc[invalid, 'conversions'] = df.loc[invalid, 'clicks']
        
        # Check 3: No null spend
        if 'spend' in df.columns:
            null_count = df['spend'].isna().sum()
            if null_count > 0:
                result.add_warning(
                    column='spend',
                    message=f"Null spend values ({null_count} rows)",
                    count=null_count
                )
                df['spend'] = df['spend'].fillna(0)
        
        # Check 4: Valid date range (not in future)
        if 'date' in df.columns:
            future = df['date'] > pd.Timestamp.now()
            if future.any():
                count = future.sum()
                result.add_warning(
                    column='date',
                    message=f"Future dates detected ({count} rows)",
                    count=count
                )
        
        return df, result


class DuckDBConstraintValidator:
    """
    Validates data using DuckDB CHECK constraints.
    
    This is the fastest validation, performed during insert.
    """
    
    @staticmethod
    def get_create_table_sql(table_name: str = "campaigns") -> str:
        """
        Get CREATE TABLE SQL with CHECK constraints.
        
        Returns:
            SQL string with all constraints
        """
        return f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            date DATE NOT NULL,
            platform VARCHAR NOT NULL,
            channel VARCHAR,
            campaign VARCHAR,
            spend DOUBLE CHECK (spend >= 0),
            impressions BIGINT CHECK (impressions >= 0),
            clicks BIGINT CHECK (clicks >= 0 AND clicks <= impressions),
            conversions BIGINT CHECK (conversions >= 0 AND conversions <= clicks),
            revenue DOUBLE CHECK (revenue >= 0),
            funnel VARCHAR,
            device VARCHAR,
            region VARCHAR,
            objective VARCHAR,
            ad_type VARCHAR
        );
        """
    
    @staticmethod
    def validate_with_duckdb(df: pd.DataFrame, conn) -> ValidationResult:
        """
        Validate DataFrame by attempting insert into temp table with constraints.
        
        Args:
            df: DataFrame to validate
            conn: DuckDB connection
        
        Returns:
            ValidationResult with any constraint violations
        """
        result = ValidationResult()
        result.row_count = len(df)
        
        try:
            # Create temp table with constraints
            conn.execute("""
                CREATE TEMP TABLE IF NOT EXISTS _validation_temp (
                    spend DOUBLE CHECK (spend >= 0),
                    clicks BIGINT CHECK (clicks >= 0),
                    impressions BIGINT CHECK (impressions >= 0)
                )
            """)
            
            # Try to insert
            conn.register('_df_temp', df)
            conn.execute("""
                INSERT INTO _validation_temp
                SELECT spend, clicks, impressions FROM _df_temp
            """)
            
            # If we get here, validation passed
            result.valid_rows = len(df)
            result.passed = True
            
            # Cleanup
            conn.execute("DROP TABLE IF EXISTS _validation_temp")
            
        except Exception as e:
            result.add_error(
                column='constraint',
                message=str(e),
                count=1
            )
            result.passed = False
        
        return result


def validate_dataframe(
    df: pd.DataFrame,
    strict: bool = False
) -> Tuple[pd.DataFrame, ValidationResult]:
    """
    Convenience function to validate a DataFrame.
    
    Args:
        df: Input DataFrame
        strict: If True, fail on any validation error
    
    Returns:
        Tuple of (validated DataFrame, ValidationResult)
    """
    validator = DataValidator(strict=strict)
    return validator.validate(df)
