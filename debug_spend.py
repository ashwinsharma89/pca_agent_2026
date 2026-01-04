
import duckdb
import pandas as pd
import os
from datetime import timedelta

def analyze_spend():
    parquet_path = os.path.join(os.getcwd(), "data", "campaigns.parquet")
    if not os.path.exists(parquet_path):
        print("No data found.")
        return

    conn = duckdb.connect()
    
    # 1. Total Spend (All Time)
    # Using the same Coalesce logic as the API
    total_query = """
    SELECT 
        SUM(COALESCE("Total Spent", 0)) as total_spend,
        MIN("Date") as min_date,
        MAX("Date") as max_date,
        COUNT(*) as total_rows
    FROM '{}'
    """.format(parquet_path)
    
    print("--- GLOBAL STATS (What Upload Page likely saw) ---")
    res = conn.execute(total_query).fetchone()
    total_spend = res[0]
    min_date = res[1]
    max_date = res[2]
    print(f"Total Spend: ${total_spend:,.2f}")
    print(f"Date Range: {min_date} to {max_date}")
    print(f"Total Rows: {res[3]}")
    
    # 2. Last 30 Days (What Dashboard likely shows)
    if max_date:
        # extract date part if timestamp
        if hasattr(max_date, 'date'):
            end_date = max_date.date()
        else:
            end_date = max_date # fallback
            
        start_date = end_date - timedelta(days=30)
        
        print(f"\n--- DASHBOARD WINDOW ({start_date} to {end_date}) ---")
        window_query = """
        SELECT 
            SUM(COALESCE("Total Spent", 0)) as window_spend,
            COUNT(*) as window_rows
        FROM '{}'
        WHERE "Date" >= ? AND "Date" <= ?
        """.format(parquet_path)
        
        # Note: Depending on how DuckDB handles timestamp comparison with date, 
        # we might need to cast. But let's try direct parameter passing first.
        # Ensure we pass datetime objects if column is TIMESTAMP
        
        w_res = conn.execute(window_query, [start_date, end_date]).fetchone()
        window_spend = w_res[0] or 0
        window_rows = w_res[1]
        
        print(f"Window Spend: ${window_spend:,.2f}")
        print(f"Window Rows: {window_rows}")
        
        diff = total_spend - window_spend
        print(f"\nDifference (Hidden by Filter): ${diff:,.2f}")
        
    # 3. Check for 'Empty' Spend Rows (Mapping Check)
    print("\n--- MAPPING CHECK ---")
    null_spend = conn.execute(f'SELECT COUNT(*) FROM "{parquet_path}" WHERE "Total Spent" IS NULL OR "Total Spent" = 0').fetchone()[0]
    print(f"Rows with 0 or NULL Spend: {null_spend}")

if __name__ == "__main__":
    analyze_spend()
