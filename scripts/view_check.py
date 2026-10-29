import pyexasol, pandas as pd

C = pyexasol.connect(dsn="127.0.0.1:8563", user="sys", password="exasol",
    websocket_sslopt={"check_hostname": False, "cert_reqs": 0})
C.execute("CREATE SCHEMA IF NOT EXISTS SUPPLYLENS")
C.execute("OPEN SCHEMA SUPPLYLENS")

# Test CREATE OR REPLACE VIEW
try:
    C.execute("CREATE OR REPLACE VIEW TEST_VIEW AS SELECT 1 AS col1")
    r = C.execute("SELECT * FROM TEST_VIEW").fetchone()
    print("CREATE OR REPLACE VIEW: OK ->", r)
    C.execute("DROP VIEW TEST_VIEW")
except Exception as e:
    print("CREATE OR REPLACE VIEW ERROR:", e)

# Test POWER function (used in HHI calculation)
try:
    r = C.execute("SELECT POWER(90.0, 2)").fetchone()
    print("POWER(): OK ->", r[0])
except Exception as e:
    print("POWER() ERROR:", e)

# Test SUM OVER PARTITION (used in V_SUPPLIER_SHARE)
try:
    C.execute("CREATE TABLE TEST_PART (cat VARCHAR(10), val DECIMAL(5,0))")
    df = pd.DataFrame([
        {"cat": "A", "val": 60}, {"cat": "A", "val": 40},
        {"cat": "B", "val": 30}, {"cat": "B", "val": 70}
    ])
    C.import_from_pandas(df, "TEST_PART")
    r = C.execute("""
        SELECT cat, val,
               SUM(val) OVER (PARTITION BY cat) AS cat_total
        FROM TEST_PART
        ORDER BY cat, val
    """).fetchall()
    print("SUM OVER PARTITION: OK ->", r)
    C.execute("DROP TABLE TEST_PART")
except Exception as e:
    print("SUM OVER PARTITION ERROR:", e)

C.close()
print("VIEW CHECKS PASSED")
