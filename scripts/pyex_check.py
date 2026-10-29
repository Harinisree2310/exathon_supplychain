import pyexasol, pandas as pd, traceback, sys

try:
    C = pyexasol.connect(
        dsn="127.0.0.1:8563",
        user="sys",
        password="exasol",
        websocket_sslopt={"check_hostname": False, "cert_reqs": 0},
    )
    print("connected OK")
    C.execute("CREATE SCHEMA IF NOT EXISTS SUPPLYLENS")
    C.execute("OPEN SCHEMA SUPPLYLENS")
    print("schema OK")

    try:
        C.execute("DROP TABLE IF EXISTS PYEX_TEST")
    except Exception:
        pass

    C.execute("CREATE TABLE PYEX_TEST (id DECIMAL(10,0), name VARCHAR(100))")
    print("table created")

    df = pd.DataFrame([{"id": 1, "name": "hello"}, {"id": 2, "name": "world"}])
    C.import_from_pandas(df, "PYEX_TEST")
    cnt = C.execute("SELECT COUNT(*) FROM PYEX_TEST").fetchone()
    print("import_from_pandas count:", cnt[0])

    C.execute("DROP TABLE PYEX_TEST")
    C.close()
    print("ALL CHECKS PASSED")
    sys.exit(0)
except Exception as e:
    traceback.print_exc()
    sys.exit(1)
