
import sqlglot
from sqlglot import exp

sql = "SELECT * FROM information_schema.tables"
parsed = sqlglot.parse_one(sql)
print(f"SQL: {sql}")
for node in parsed.walk():
    if isinstance(node, exp.Table):
        print(f"Node: {node}")
        print(f"Name: {node.name}")
        print(f"DB (Schema): {node.db}")
        print(f"Catalog: {node.catalog}")
