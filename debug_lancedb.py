
import lancedb
import shutil
from pathlib import Path
from datetime import datetime

# Setup
DB_PATH = Path("data/debug_lancedb")
if DB_PATH.exists():
    shutil.rmtree(DB_PATH)
    
db = lancedb.connect(DB_PATH)
table_name = "debug_table"

# Mock Data
documents = ["Total spend?", "What is the spend?"]
# Simulating 384-d vectors (all 0.1)
vec = [0.1] * 20 # Reduced dim for debug print, doesn't matter for lancedb logic usually 
# Start with small dim to see if it complains. 
# actually lancedb infers dim from data.
vec = [0.1] * 384

data = []
for doc in documents:
    data.append({
        "vector": vec,
        "text": doc,
        "created_at": datetime.now().isoformat(),
        "id": 1
    })

print(f"Creating table {table_name}...")
tbl = db.create_table(table_name, data=data)
print(f"Table created. Rows: {len(tbl)}")

try:
    tbl.create_fts_index("text")
    print("FTS index created.")
except Exception as e:
    print(f"FTS index failed: {e}")

# Search
print("Searching...")
query_vec = vec
# Pure Vector Search
res_vec = tbl.search(query_vec).limit(1).to_list()
print("Vector Search Result keys:", res_vec[0].keys())
print("Vector Search Result [0]:", res_vec[0])

# Hybrid Search
try:
    res_hybrid = tbl.search(query_vec, query_type="hybrid").limit(1).to_list()
    print("Hybrid Search Result keys:", res_hybrid[0].keys())
except Exception as e:
    print(f"Hybrid search failed: {e}")

# Cleanup
shutil.rmtree(DB_PATH)
