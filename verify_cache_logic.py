
import shutil
from pathlib import Path
from src.intelligence.lancedb_manager import LanceDBManager
from src.intelligence.semantic_cache import SemanticCache
from loguru import logger
import sys

# Configure logger to stdout
logger.remove()
logger.add(sys.stdout, level="DEBUG")

TEST_DB_PATH = Path("data/verify_lancedb")
if TEST_DB_PATH.exists():
    shutil.rmtree(TEST_DB_PATH)

print("Initializing LanceDBManager...")
manager = LanceDBManager(db_path=TEST_DB_PATH)

print("Initializing SemanticCache...")
cache = SemanticCache(db_manager=manager)

question = "What is the total spend?"
sql = "SELECT SUM(spend) FROM campaigns"

print("Setting cache...")
cache.set(question, sql)

print("Getting cache...")
result = cache.get(question)

if result:
    print("SUCCESS: Cache hit!")
    print(result)
else:
    print("FAILURE: Cache miss (returned None)")

# Cleanup
if TEST_DB_PATH.exists():
    shutil.rmtree(TEST_DB_PATH)
