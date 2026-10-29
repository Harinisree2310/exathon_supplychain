import pyexasol, pandas as pd
C = pyexasol.connect(dsn="127.0.0.1:8563", user="sys", password="exasol",
    websocket_sslopt={"check_hostname": False, "cert_reqs": 0})
C.execute("CREATE SCHEMA IF NOT EXISTS SUPPLYLENS")
C.execute("OPEN SCHEMA SUPPLYLENS")
C.execute("CREATE TABLE TEST_TRUNC (id DECIMAL(5,0))")
df = pd.DataFrame([{"id": i} for i in range(5)])
C.import_from_pandas(df, "TEST_TRUNC")

# Test TRUNCATE
try:
    C.execute("TRUNCATE TABLE TEST_TRUNC")
    cnt = C.execute("SELECT COUNT(*) FROM TEST_TRUNC").fetchone()
    print("TRUNCATE: OK, count after:", cnt[0])
except Exception as e:
    print("TRUNCATE ERROR:", e)

C.import_from_pandas(df, "TEST_TRUNC")
# Test LIMIT
try:
    r = C.execute("SELECT id FROM TEST_TRUNC ORDER BY id LIMIT 2").fetchall()
    print("LIMIT: OK ->", r)
except Exception as e:
    print("LIMIT ERROR:", e)
    # Exasol may use FETCH FIRST n ROWS instead
    try:
        r = C.execute("SELECT id FROM TEST_TRUNC ORDER BY id FETCH FIRST 2 ROWS ONLY").fetchall()
        print("FETCH FIRST: OK ->", r)
    except Exception as e2:
        print("FETCH FIRST also failed:", e2)

C.execute("DROP TABLE TEST_TRUNC")
C.close()
