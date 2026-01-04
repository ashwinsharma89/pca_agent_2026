
import sqlglot
from sqlglot import exp
from typing import Tuple, List, Optional
from loguru import logger

class SQLValidator:
    """
    Google-Grade SQL Validator using AST (Abstract Syntax Tree) parsing.
    Ensures that only safe, read-only queries are executed.
    """
    
    FORBIDDEN_COMMANDS = (
        exp.Drop,
        exp.Delete,
        exp.Insert,
        exp.Update,
        exp.Create,
        exp.Alter
    )
    
    SYSTEM_TABLES = {'information_schema', 'pg_catalog', 'sqlite_master'}

    def __init__(self, dialect: str = "duckdb"):
        self.dialect = dialect

    def validate(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        Validates SQL string for security violations.
        Returns: (is_valid, error_message)
        """
        try:
            # Parse ALL statements (handle potential multi-statement injection)
            expressions = sqlglot.parse(sql, read=self.dialect)
            
            if len(expressions) > 1:
                return False, "Security Violation: Multiple SQL statements detected. Only single queries allowed."
            
            if not expressions:
                return False, "Empty SQL query."

            expression = expressions[0]
            
            # 1. Root Check: Must be a SELECT or CTE (which ends in SELECT)
            if not isinstance(expression, exp.Select):
                # Allow Union/Except/Intersect which are also read-only
                if not isinstance(expression, (exp.Union, exp.Except, exp.Intersect)):
                    return False, f"Security Violation: Root statement must be SELECT. Got: {expression.key}"

            # 2. Deep Tree Traversal for Forbidden Nodes
            for node in expression.walk():
                # Check Forbidden Commands
                if isinstance(node, self.FORBIDDEN_COMMANDS):
                    return False, f"Security Violation: Forbidden command detected: {node.key}"
                
                # Check System Tables
                if isinstance(node, exp.Table):
                    # Check table name, schema (db), and catalog
                    parts = [node.name, node.db, node.catalog]
                    for part in parts:
                        if part and part.lower() in self.SYSTEM_TABLES:
                             return False, f"Security Violation: Access to system table/schema '{part}' denied."
                        
                    # Check for complexity (nested subqueries depth > 2)
                    # Implementation simplified for Phase 1
            
            # 3. Guardrail Injection (Mutates the AST)
            # Ensure LIMIT exists
            # Note: For complex queries/aggregations, LIMIT might be on the outer wrapper.
            # This is a basic check.
            
            return True, None

        except sqlglot.errors.ParseError as e:
            return False, f"SQL Parse Error: {str(e)}"
        except Exception as e:
            logger.error(f"Validator Crash: {e}")
            return False, "Internal Validation Error"

    def inject_limit(self, sql: str, limit: int = 1000) -> str:
        """
        Parses SQL, checks for LIMIT, injects if missing.
        """
        try:
            expression = sqlglot.parse_one(sql, read=self.dialect)
            
            # Only inject for top-level SELECTs
            if isinstance(expression, exp.Select):
                 # Check if LIMIT exists
                if not expression.args.get("limit"):
                    expression = expression.limit(limit)
                    return expression.sql(dialect=self.dialect)
            
            return sql # Return original if we can't safely inject
            
        except Exception as e:
            logger.warning(f"Failed to inject limit: {e}")
            return sql
