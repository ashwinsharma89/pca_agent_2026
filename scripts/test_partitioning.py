
import logging
import pandas as pd
from datetime import datetime, timedelta
import shutil
import glob
import os
from src.database.duckdb_manager import get_duckdb_manager, CAMPAIGNS_DIR

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_partitioning():
    manager = get_duckdb_manager()
    
    # 1. Clear existing data
    logger.info("1. Clearing data...")
    manager.clear_data()
    
    # 2. Create mock data spanning multiple months
    logger.info("2. creating mock data...")
    dates = [
        datetime(2024, 1, 15),
        datetime(2024, 1, 20),
        datetime(2024, 2, 10),
        datetime(2024, 2, 15)
    ]
    
    data = []
    for i, date in enumerate(dates):
        data.append({
            "id": i,
            "Campaign": f"Campaign {i}",
            "Platform": "Google" if i % 2 == 0 else "Meta",
            "Date": date,
            "Spend": 100 * (i + 1),
            "Impressions": 1000 * (i + 1),
            "Clicks": 50 * (i + 1),
            "Conversions": 5 * (i + 1)
        })
    
    df = pd.DataFrame(data)
    
    # 3. Save data
    logger.info("3. Saving data...")
    manager.save_campaigns(df)
    
    # 4. Verify directory structure
    logger.info("4. Verifying partitions...")
    partitions = glob.glob(str(CAMPAIGNS_DIR / "year=*/month=*/*.parquet"))
    logger.info(f"Found {len(partitions)} partition files: {partitions}")
    
    if len(partitions) < 2:
        logger.error("❌ Failed to create partitions! Found fewer than 2 distinct month partitions.")
        exit(1)
        
    # 5. Verify Reading (Total)
    logger.info("5. Verifying Read (Total Metrics)...")
    totals = manager.get_total_metrics()
    logger.info(f"Totals: {totals}")
    
    expected_spend = sum(d['Spend'] for d in data)
    if totals['total_spend'] != expected_spend:
        logger.error(f"❌ Spend mismatch: Expected {expected_spend}, got {totals['total_spend']}")
        exit(1)
        
    # 6. Verify Reading (Filtering)
    logger.info("6. Verifying Read (Filtering Jan 2024)...")
    # DuckDB handles partitioning automatically, we can filter by normal columns
    jan_data = manager.get_campaigns(filters={'Platform': 'Google'})
    logger.info(f"Filtered Rows: {len(jan_data)}")
    
    if len(jan_data) != 2: # 0 and 2 are Google
        logger.error(f"❌ Filter mismatch: Expected 2 Google rows, got {len(jan_data)}")
        exit(1)

    logger.info("✅ SUCCESS: Partitioning and Reading working correctly.")

if __name__ == "__main__":
    test_partitioning()
