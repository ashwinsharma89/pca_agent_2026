"""
MCP Server for NL-to-SQL Engine

This server exposes the PCA Agent's natural language to SQL engine as MCP tools.
Other AI agents (Claude, etc.) can use these tools to:
- Convert natural language questions to SQL
- Execute SQL queries safely
- Get full Q&A responses with data

Usage:
    python -m src.mcp_server.nl_to_sql_server

Or configure Claude Desktop with the provided mcp_config.json
"""

import os
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    ResourceContents,
    TextResourceContents,
)

# Import our existing NL-to-SQL engine
from src.query_engine.nl_to_sql import NaturalLanguageQueryEngine
from src.query_engine.safe_query import SafeQueryExecutor

# Initialize MCP server
server = Server("pca-nl-to-sql")

# Database path
DB_PATH = str(project_root / "data" / "analytics.duckdb")

# Initialize query engine (lazy)
_query_engine = None

def get_query_engine():
    """Lazy initialization of query engine."""
    global _query_engine
    if _query_engine is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        _query_engine = NaturalLanguageQueryEngine(api_key=api_key)
        
        # Load data from DuckDB file
        import duckdb
        import pandas as pd
        conn = duckdb.connect(DB_PATH, read_only=True)
        df = conn.execute("SELECT * FROM campaigns").fetchdf()
        conn.close()
        
        # Initialize engine with the data
        _query_engine.load_data(df, "campaigns")
    return _query_engine


# =============================================================================
# TOOL DEFINITIONS
# =============================================================================

@server.list_tools()
async def list_tools():
    """List available tools."""
    return [
        Tool(
            name="nl_to_sql",
            description="Convert a natural language question about campaign data into a SQL query. "
                        "Use this when you need to generate SQL but don't need the results yet.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The natural language question to convert to SQL. "
                                       "Example: 'What are the top 5 campaigns by spend?'"
                    }
                },
                "required": ["question"]
            }
        ),
        Tool(
            name="execute_sql",
            description="Execute a SQL query on the campaign database and return results. "
                        "The query is validated for safety (only SELECT allowed).",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "The SQL query to execute. Must be a SELECT statement."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of rows to return (default: 100)",
                        "default": 100
                    }
                },
                "required": ["sql"]
            }
        ),
        Tool(
            name="ask_question",
            description="Ask a natural language question about campaign data and get a complete answer. "
                        "This combines SQL generation, execution, and answer synthesis.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to answer. Example: 'Which platform has the best ROAS?'"
                    }
                },
                "required": ["question"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Execute a tool call."""
    
    if name == "nl_to_sql":
        return await handle_nl_to_sql(arguments)
    elif name == "execute_sql":
        return await handle_execute_sql(arguments)
    elif name == "ask_question":
        return await handle_ask_question(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def handle_nl_to_sql(arguments: dict):
    """Convert natural language to SQL."""
    question = arguments.get("question", "")
    
    if not question:
        return [TextContent(type="text", text="Error: 'question' is required")]
    
    try:
        engine = get_query_engine()
        # generate_sql returns a string, not a dict
        sql = engine.generate_sql(question)
        
        response = {
            "success": True,
            "sql": sql,
            "question": question
        }
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2))]


async def handle_execute_sql(arguments: dict):
    """Execute SQL query safely."""
    sql = arguments.get("sql", "")
    limit = arguments.get("limit", 100)
    
    if not sql:
        return [TextContent(type="text", text="Error: 'sql' is required")]
    
    try:
        # Use safe query executor
        executor = SafeQueryExecutor()
        
        # Validate the query first (returns bool)
        is_valid = executor.validate_sql(sql)
        if not is_valid:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "error": "Query validation failed: Only SELECT queries allowed"
            }, indent=2))]
        
        # Execute the query
        import duckdb
        conn = duckdb.connect(DB_PATH, read_only=True)
        
        # Add limit if not present
        if "LIMIT" not in sql.upper():
            sql = f"{sql.rstrip(';')} LIMIT {limit}"
        
        result = conn.execute(sql).fetchdf()
        conn.close()
        
        # Convert to serializable format
        data = result.head(limit).to_dict(orient="records")
        columns = list(result.columns)
        
        response = {
            "success": True,
            "row_count": len(data),
            "columns": columns,
            "data": data
        }
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2))]


async def handle_ask_question(arguments: dict):
    """Full Q&A pipeline."""
    question = arguments.get("question", "")
    
    if not question:
        return [TextContent(type="text", text="Error: 'question' is required")]
    
    try:
        engine = get_query_engine()
        result = engine.ask(question)
        
        # Convert DataFrame results to list if present
        data = []
        if result.get("results") is not None and hasattr(result["results"], 'to_dict'):
            data = result["results"].head(50).to_dict(orient="records")
        
        response = {
            "success": result.get("success", False),
            "answer": result.get("answer", ""),
            "sql": result.get("sql_query", ""),
            "data": data,
            "row_count": len(data),
            "error": result.get("error")
        }
        
        return [TextContent(type="text", text=json.dumps(response, indent=2, default=str))]
    
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2))]


# =============================================================================
# RESOURCE DEFINITIONS
# =============================================================================

@server.list_resources()
async def list_resources():
    """List available resources."""
    return [
        Resource(
            uri="schema://campaigns",
            name="Campaign Database Schema",
            description="Schema information for the campaigns database including tables and columns",
            mimeType="application/json"
        )
    ]


@server.read_resource()
async def read_resource(uri: str):
    """Read a resource."""
    if uri == "schema://campaigns":
        return await get_schema_resource()
    else:
        raise ValueError(f"Unknown resource: {uri}")


async def get_schema_resource():
    """Get the database schema as a resource."""
    try:
        import duckdb
        conn = duckdb.connect(DB_PATH, read_only=True)
        
        # Get table info
        tables = conn.execute("SHOW TABLES").fetchall()
        
        schema_info = {"tables": {}}
        
        for (table_name,) in tables:
            columns = conn.execute(f"DESCRIBE {table_name}").fetchall()
            schema_info["tables"][table_name] = {
                "columns": [
                    {"name": col[0], "type": col[1]} 
                    for col in columns
                ]
            }
        
        conn.close()
        
        return ResourceContents(
            uri="schema://campaigns",
            contents=[
                TextResourceContents(
                    uri="schema://campaigns",
                    mimeType="application/json",
                    text=json.dumps(schema_info, indent=2)
                )
            ]
        )
    
    except Exception as e:
        return ResourceContents(
            uri="schema://campaigns",
            contents=[
                TextResourceContents(
                    uri="schema://campaigns",
                    mimeType="application/json",
                    text=json.dumps({"error": str(e)})
                )
            ]
        )


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

async def main():
    """Run the MCP server."""
    print("Starting PCA NL-to-SQL MCP Server...", file=sys.stderr)
    print(f"Database: {DB_PATH}", file=sys.stderr)
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
