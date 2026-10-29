import pyexasol, sys, traceback
C = pyexasol.connect(dsn="127.0.0.1:8563", user="sys", password="exasol",
    websocket_sslopt={"check_hostname": False, "cert_reqs": 0})
C.execute("CREATE SCHEMA IF NOT EXISTS SUPPLYLENS")
C.execute("OPEN SCHEMA SUPPLYLENS")

# Test CREATE TABLE IF NOT EXISTS (Exasol 2026 syntax check)
try:
    C.execute("CREATE TABLE IF NOT EXISTS TEST_CINE (id DECIMAL(10,0))")
    C.execute("DROP TABLE IF EXISTS TEST_CINE")
    print("CREATE TABLE IF NOT EXISTS: OK")
except Exception as e:
    print("CREATE TABLE IF NOT EXISTS ERROR:", e)

# Test BOOLEAN column type
try:
    C.execute("CREATE TABLE IF NOT EXISTS TEST_BOOL (flag BOOLEAN)")
    C.execute("DROP TABLE IF EXISTS TEST_BOOL")
    print("BOOLEAN column: OK")
except Exception as e:
    print("BOOLEAN column ERROR:", e)
    print("Will use CHAR(1) or DECIMAL(1,0) instead")

# Test ADD_DAYS function
try:
    r = C.execute("SELECT ADD_DAYS(CURRENT_DATE, -30)").fetchone()
    print("ADD_DAYS function: OK ->", r[0])
except Exception as e:
    print("ADD_DAYS ERROR:", e)

# Test RANK() window function
try:
    C.execute("""
        CREATE TABLE IF NOT EXISTS TEST_RANK (val DECIMAL(5,0))
    """)
    C.import_from_pandas(
        __import__("pandas").DataFrame([{"val": 1}, {"val": 2}]),
        "TEST_RANK"
    )
    r = C.execute("SELECT val, RANK() OVER (ORDER BY val) AS rnk FROM TEST_RANK").fetchall()
    print("RANK() window function: OK ->", r)
    C.execute("DROP TABLE IF EXISTS TEST_RANK")
except Exception as e:
    print("RANK() ERROR:", e)

# Test DATE_TRUNC
try:
    r = C.execute("SELECT DATE_TRUNC('MONTH', CURRENT_DATE)").fetchone()
    print("DATE_TRUNC: OK ->", r[0])
except Exception as e:
    print("DATE_TRUNC ERROR:", e)
    try:
        r = C.execute("SELECT TRUNC(CURRENT_DATE, 'MM')").fetchone()
        print("TRUNC(MM) alternative: OK ->", r[0])
    except Exception as e2:
        print("TRUNC also failed:", e2)

C.close()
