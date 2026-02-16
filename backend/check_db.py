import psycopg2
import os

password = "sana"
user = "postgres"
host = "localhost"
port = "5432"

def test_connection(dbname):
    print(f"\nTesting connection to '{dbname}'...")
    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        print(f"SUCCESS: Connected to '{dbname}'")
        return conn
    except Exception as e:
        print(f"FAILURE: Could not connect to '{dbname}': {e}")
        return None

# 1. Try connecting to default 'postgres' DB to list all DBs
conn = test_connection("postgres")
if conn:
    try:
        cur = conn.cursor()
        cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
        rows = cur.fetchall()
        print("\nAvailable Databases:")
        for row in rows:
            print(f" - {row[0]}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error listing databases: {e}")

# 2. Test specific project DBs
test_connection("lung_disease_db")
test_connection("lung_db")
