
import sys
import os
sys.path.append(os.path.abspath(os.curdir))
from src.database.duckdb_manager import get_duckdb_manager
import pandas as pd

def check_dates():
    mgr = get_duckdb_manager()
    if not mgr.has_data():
        print("No data in DuckDB.")
        return

    df = mgr.get_campaigns()
    
    # Try to find date column
    date_col = None
    for col in df.columns:
        if 'date' in col.lower() or 'time' in col.lower():
            date_col = col
            break
            
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')
        min_date = df[date_col].min()
        max_date = df[date_col].max()
        print(f"Date Column: {date_col}")
        print(f"Min Date: {min_date}")
        print(f"Max Date: {max_date}")
        print(f"Total Rows: {len(df)}")
    else:
        print("No date column found.")
        print("Columns:", df.columns.tolist())

if __name__ == "__main__":
    check_dates()
