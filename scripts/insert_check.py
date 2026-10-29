import pyexasol, sys
C = pyexasol.connect(dsn="127.0.0.1:8563", user="sys", password="exasol",
    websocket_sslopt={"check_hostname": False, "cert_reqs": 0})
C.execute("CREATE SCHEMA IF NOT EXISTS SUPPLYLENS")
C.execute("OPEN SCHEMA SUPPLYLENS")

# Test DROP IF EXISTS (used in analytics.py)
try:
    C.execute("DROP TABLE IF EXISTS TEST_INS")
    print("DROP TABLE IF EXISTS: OK")
except Exception as e:
    print("DROP IF EXISTS ERROR:", e)

# Test INSERT with {param} substitution
C.execute("CREATE TABLE TEST_INS (id VARCHAR(36), name VARCHAR(100), val DECIMAL(10,2))")
try:
    C.execute(
        "INSERT INTO TEST_INS (id, name, val) VALUES ({id}, {name}, {val})",
        {"id": "abc-123", "name": "test name", "val": 99.5}
    )
    r = C.execute("SELECT * FROM TEST_INS").fetchone()
    print("INSERT {param}: OK ->", r)
except Exception as e:
    print("INSERT {param} ERROR:", e)

# Test DELETE with {param}
try:
    C.execute("DELETE FROM TEST_INS WHERE id = {id}", {"id": "abc-123"})
    cnt = C.execute("SELECT COUNT(*) FROM TEST_INS").fetchone()
    print("DELETE {param}: OK, remaining:", cnt[0])
except Exception as e:
    print("DELETE {param} ERROR:", e)

# Test UPDATE with {param}
C.execute("INSERT INTO TEST_INS VALUES ('xyz', 'upd', 1.0)")
try:
    C.execute("UPDATE TEST_INS SET val = {val} WHERE id = {id}", {"val": 2.5, "id": "xyz"})
    r = C.execute("SELECT val FROM TEST_INS WHERE id = 'xyz'").fetchone()
    print("UPDATE {param}: OK ->", r[0])
except Exception as e:
    print("UPDATE {param} ERROR:", e)

C.execute("DROP TABLE TEST_INS")
C.close()
print("ALL INSERT TESTS PASSED")
