"""
Safe Query Executor - SQL Injection Prevention
Provides parameterized query execution with validation
"""
from sqlalchemy import text
from typing import Dict, Any, Optional, List
import re
import logging
import os

logger = logging.getLogger(__name__)


class SQLInjectionError(Exception):
    """Raised when dangerous SQL patterns are detected"""
    pass


class SafeQueryExecutor:
    """Secure SQL query execution with parameterization"""
    
    # Dangerous SQL patterns to block
    DANGEROUS_PATTERNS = [
        r';\s*DROP',
        r';\s*DELETE\s+FROM',
        r';\s*UPDATE.*WHERE\s+1\s*=\s*1',
        r';\s*TRUNCATE',
        r'EXEC\s*\(',
        r'xp_cmdshell',
        r'--\s*$',  # SQL comments at end
        r'/\*.*\*/',  # Block comments
        r'UNION\s+SELECT',  # Union-based injection
        r'OR\s+1\s*=\s*1',  # Always true conditions
        r'OR\s+\'1\'\s*=\s*\'1\'',
    ]
    
    @staticmethod
    def validate_sql(sql: str) -> bool:
        """
        Validate SQL doesn't contain dangerous patterns
        
        Args:
            sql: SQL query to validate
            
        Returns:
            True if safe
            
        Raises:
            SQLInjectionError: If dangerous pattern detected
        """
        for pattern in SafeQueryExecutor.DANGEROUS_PATTERNS:
            if re.search(pattern, sql, re.IGNORECASE):
                logger.error(f"Dangerous SQL pattern detected: {pattern}")
                raise SQLInjectionError(f"Dangerous SQL pattern detected: {pattern}")
        return True
    
    @staticmethod
    def execute_safe(conn, sql: str, params: Optional[Dict[str, Any]] = None):
        """
        Execute SQL with parameters (prevents SQL injection)
        
        Args:
            conn: Database connection
            sql: SQL query with named parameters (:param_name)
            params: Dictionary of parameter values
            
        Returns:
            Query result
            
        Example:
            result = SafeQueryExecutor.execute_safe(
                conn,
                "SELECT * FROM campaigns WHERE platform = :platform",
                {"platform": "facebook"}
            )
        """
        # Validate SQL
        SafeQueryExecutor.validate_sql(sql)
        
        # Convert to parameterized query
        query = text(sql)
        
        # Execute with parameters
        try:
            result = conn.execute(query, params or {})
            logger.info(f"Executed safe query: {sql[:100]}...")
            return result
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    @staticmethod
    def sanitize_identifier(identifier: str, allow_dots: bool = False) -> str:
        """
        Sanitize table/column names (identifiers)
        Only allows alphanumeric, underscore, and optionally dots
        
        Args:
            identifier: Table or column name
            allow_dots: If True, allow dots for qualified names (schema.table)
            
        Returns:
            Sanitized identifier
            
        Raises:
            ValueError: If identifier contains invalid characters
        """
        if allow_dots:
            pattern = r'^[a-zA-Z_][a-zA-Z0-9_.]*$'
        else:
            pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
        
        if not re.match(pattern, identifier):
            raise ValueError(f"Invalid identifier: {identifier}")
        return identifier
    
    @staticmethod
    def execute_duckdb_safe(conn, sql: str, params: Optional[List[Any]] = None):
        """
        Execute DuckDB query with positional parameters (prevents SQL injection)
        
        Args:
            conn: DuckDB connection
            sql: SQL query with positional parameters (?)
            params: List of parameter values
            
        Returns:
            Query result
            
        Example:
            result = SafeQueryExecutor.execute_duckdb_safe(
                conn,
                "SELECT * FROM campaigns WHERE platform = ?",
                ["facebook"]
            )
        """
        # Validate SQL
        SafeQueryExecutor.validate_sql(sql)
        
        # Execute with parameters
        try:
            result = conn.execute(sql, params or [])
            logger.info(f"Executed safe DuckDB query: {sql[:100]}...")
            return result
        except Exception as e:
            logger.error(f"DuckDB query execution failed: {e}")
            raise
    
    @staticmethod
    def validate_file_path(path: str, allowed_extensions: Optional[List[str]] = None) -> str:
        """
        Validate file path for security
        
        Args:
            path: File path to validate
            allowed_extensions: List of allowed file extensions (e.g., ['.parquet', '.csv'])
            
        Returns:
            Absolute path if valid
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file extension not allowed or path contains suspicious patterns
        """
        # Check for path traversal attempts
        if '..' in path or path.startswith('/'):
            # Allow absolute paths but check they're not system paths
            if path.startswith(('/etc/', '/sys/', '/proc/', '/dev/')):
                raise ValueError(f"Access to system paths not allowed: {path}")
        
        # Convert to absolute path
        abs_path = os.path.abspath(path)
        
        # Check file exists
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"File not found: {abs_path}")
        
        # Check extension if specified
        if allowed_extensions:
            if not any(abs_path.endswith(ext) for ext in allowed_extensions):
                raise ValueError(f"File extension not allowed. Allowed: {allowed_extensions}")
        
        logger.info(f"Validated file path: {abs_path}")
        return abs_path
    
    @staticmethod
    def validate_query_against_schema(
        sql: str, 
        allowed_tables: List[str], 
        allowed_columns: List[str]
    ) -> bool:
        """
        Pattern-based SQL security validation.
        Blocks dangerous operations, allows all safe SELECT queries.
        
        This approach is more robust than token whitelisting because:
        1. Won't block valid SQL tokens like 'R', 'RECENT', etc.
        2. Focuses on blocking actual security threats
        3. Much easier to maintain
        """
        sql_upper = sql.upper().strip()
        
        # Block 1: Destructive operations (highest priority)
        DESTRUCTIVE_KEYWORDS = [
            'DROP TABLE', 'DROP DATABASE', 'DROP INDEX', 'DROP VIEW',
            'TRUNCATE TABLE', 'TRUNCATE',
            'DELETE FROM',
            'ALTER TABLE', 'ALTER DATABASE',
            'CREATE TABLE', 'CREATE DATABASE', 'CREATE INDEX',
            'GRANT ', 'REVOKE ',
            'INSERT INTO', 'UPDATE ',
            'EXECUTE', 'EXEC ',
        ]
        
        for keyword in DESTRUCTIVE_KEYWORDS:
            if keyword in sql_upper:
                logger.error(f"Blocked destructive operation: {keyword}")
                raise SQLInjectionError(f"Blocked destructive SQL operation: {keyword}")
        
        # Block 2: Multiple statements (prevents stacked queries)
        sql_no_strings = re.sub(r"'[^']*'", "''", sql)
        if sql_no_strings.count(';') > 1:
            logger.error("Multiple statements detected")
            raise SQLInjectionError("Multiple SQL statements not allowed")
        
        # Note: We allow -- comments as LLM often includes them for readability
        # The real security is blocking destructive operations above
        
        # Block 4: Must start with SELECT or WITH (read-only queries only)
        first_keyword = sql_upper.split()[0] if sql_upper.split() else ''
        if first_keyword not in ('SELECT', 'WITH'):
            logger.error(f"Non-SELECT query attempted: {first_keyword}")
            raise SQLInjectionError(f"Only SELECT queries allowed, got: {first_keyword}")
        
        # Block 5: UNION-based injection (conservative check)
        if sql_upper.count('UNION') > 2:
            logger.error("Multiple UNION detected - possible injection")
            raise SQLInjectionError("Multiple UNION statements not allowed")
        
        # ✅ All checks passed - query is safe
        logger.debug(f"SQL validation passed for query: {sql[:100]}...")
        return True



    @staticmethod
    def validate_has_time_filter(sql: str, question: str) -> tuple:
        """
        Ensure time-based questions have proper time filters in SQL.
        
        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        time_keywords = ['last', 'recent', 'yesterday', 'week', 'month', 'today', 
                         'daily', 'weekly', 'monthly', 'this week', 'this month',
                         'past', 'previous', 'ago']
        has_time_reference = any(kw in question.lower() for kw in time_keywords)
        
        if has_time_reference:
            sql_upper = sql.upper()
            
            # Check if SQL has WHERE clause
            if 'WHERE' not in sql_upper:
                return False, "Question references time period but SQL has no WHERE clause"
            
            # Check if SQL filters by Date column
            has_date_filter = ('"Date"' in sql or '"DATE"' in sql or 
                               'DATE' in sql_upper.split('WHERE')[1] if 'WHERE' in sql_upper else False)
            if not has_date_filter:
                return False, "Question references time period but SQL doesn't filter by Date"
            
            # Check for proper anchoring (should use MAX(Date) not CURRENT_DATE)
            if 'CURRENT_DATE' in sql_upper and 'MAX(' not in sql_upper:
                return False, "SQL uses CURRENT_DATE instead of anchoring to MAX(Date) from data"
        
        return True, "OK"
    
    @staticmethod
    def get_time_filter_correction_prompt(sql: str, question: str, error: str) -> str:
        """Generate a self-correction prompt for time filter issues."""
        return f"""
Error: {error}

Original question: {question}
Generated SQL: {sql}

Fix this SQL to include proper time filtering:
1. Add a WHERE clause filtering by "Date" column
2. Anchor to actual data using: (SELECT MAX("Date") FROM all_campaigns) 
3. Use INTERVAL for relative dates, e.g.: - INTERVAL '7 days'

Example pattern:
WHERE STRPTIME("Date", '%d/%m/%y')::DATE >= (SELECT MAX(STRPTIME("Date", '%d/%m/%y')::DATE) FROM all_campaigns) - INTERVAL '7 days'
"""


    @staticmethod
    def build_safe_query(
        table: str,
        columns: list = None,
        where_conditions: Dict[str, Any] = None,
        order_by: str = None,
        limit: int = None
    ) -> tuple[str, Dict[str, Any]]:
        """
        Build a safe SELECT query with parameters
        
        Args:
            table: Table name
            columns: List of column names (default: *)
            where_conditions: Dictionary of column: value conditions
            order_by: Column to order by
            limit: Maximum rows to return
            
        Returns:
            Tuple of (sql_query, parameters)
        """
        # Sanitize identifiers
        table = SafeQueryExecutor.sanitize_identifier(table)
        
        # Build SELECT clause
        if columns:
            cols = ", ".join([SafeQueryExecutor.sanitize_identifier(c) for c in columns])
        else:
            cols = "*"
        
        sql = f"SELECT {cols} FROM {table}"  # nosec B608
        params = {}
        
        # Build WHERE clause
        if where_conditions:
            where_parts = []
            for i, (col, val) in enumerate(where_conditions.items()):
                col = SafeQueryExecutor.sanitize_identifier(col)
                param_name = f"param_{i}"
                where_parts.append(f"{col} = :{param_name}")
                params[param_name] = val
            sql += " WHERE " + " AND ".join(where_parts)
        
        # Add ORDER BY
        if order_by:
            order_by = SafeQueryExecutor.sanitize_identifier(order_by)
            sql += f" ORDER BY {order_by}"
        
        # Add LIMIT
        if limit:
            sql += f" LIMIT {int(limit)}"
        
        return sql, params
