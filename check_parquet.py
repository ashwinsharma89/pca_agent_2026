
import duckdb
import os

def check_schema():
    # Path to parquet file
    parquet_path = os.path.join(os.getcwd(), "data", "campaigns.parquet")
    print(f"Checking {parquet_path}")
    
    if not os.path.exists(parquet_path):
        print("Parquet file not found")
        return

    conn = duckdb.connect()
    # Describe table from parquet
    print("\n--- SCHEMA ---")
    conn.execute(f"DESCRIBE SELECT * FROM '{parquet_path}'")
    print(conn.fetchall())
    
    print("\n--- DATE SAMPLE (RAW) ---")
    conn.execute(f"SELECT Date FROM '{parquet_path}' LIMIT 5")
    print(conn.fetchall())
    
    print("\n--- SQL TEST: year(Date) ---")
    try:
        conn.execute(f"SELECT year(Date) FROM '{parquet_path}' LIMIT 5")
        print(conn.fetchall())
    except Exception as e:
        print(f"year() failed: {e}")
        
    print("\n--- SQL TEST: strptime (OLD LOGIC) ---")
    try:
        # Test if strptime works on this column (implies it's a string)
        conn.execute(f"SELECT strptime(Date, '%d/%m/%y') FROM '{parquet_path}' LIMIT 5")
        print(conn.fetchall())
    except Exception as e:
        print(f"strptime failed (Expected if Date is Timestamp): {e}")

if __name__ == "__main__":
    check_schema()
