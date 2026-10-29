"""Quick pyexasol connection smoke-test."""
import sys
import pyexasol

try:
    conn = pyexasol.connect(
        dsn="127.0.0.1:8563",
        user="sys",
        password="exasol",
        websocket_sslopt={"check_hostname": False, "cert_reqs": 0},
    )
    row = conn.execute("SELECT 1 AS test").fetchone()
    print(f"CONNECTION OK — SELECT 1 = {row[0]}")
    ver = conn.execute("SELECT PARAM_VALUE FROM EXA_METADATA WHERE PARAM_NAME='databaseProductVersion'").fetchone()
    print(f"Exasol version: {ver[0] if ver else 'unknown'}")
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1)
