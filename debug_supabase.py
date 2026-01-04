
import psycopg2
import sys
from urllib.parse import quote_plus

host = "db.hxhhctwnzeiopupavbpw.supabase.co"
user = "postgres"
password = "Q21175bptp!"
dbname = "postgres"
port = 5432

print(f"Testing connection to {host}...")

# 1. Try raw parameters
try:
    print("\nAttempt 1: Raw parameters with sslmode='require'")
    conn = psycopg2.connect(
        host=host,
        user=user,
        password=password,
        dbname=dbname,
        port=port,
        sslmode='require'
    )
    print("SUCCESS: Connected with raw parameters!")
    conn.close()
except Exception as e:
    print(f"FAILURE 1: {e}")

# 2. Try URI
try:
    encoded_pass = quote_plus(password)
    uri = f"postgresql://{user}:{encoded_pass}@{host}:{port}/{dbname}?sslmode=require"
    print(f"\nAttempt 2: URI: postgresql://{user}:REDACTED@{host}:{port}/{dbname}?sslmode=require")
    # print(f"DEBUG URI: {uri}") 
    conn = psycopg2.connect(uri)
    print("SUCCESS: Connected with URI!")
    conn.close()
except Exception as e:
    print(f"FAILURE 2: {e}")
