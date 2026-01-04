
import sqlglot
from sqlglot import exp

sql = "DROP TABLE campaigns"
parsed = sqlglot.parse(sql, read="duckdb")
if parsed:
    node = parsed[0]
    print(f"SQL: {sql}")
    print(f"Type: {type(node)}")
    print(f"Is instance of exp.Drop? {isinstance(node, exp.Drop)}")
else:
    print("Failed to parse")
