"""Run schema init + seed load from project root."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.db.connection import get_db
from app.db.schema_init import init_schema
from app.db.seed_loader import load_synthetic_data

configure_logging()
settings = get_settings()

print(f"Connecting to Exasol at {settings.exasol_dsn} ...")
with get_db() as conn:
    print("Connected. Initialising schema ...")
    init_schema(conn, settings.exasol_schema)
    print("Schema ready. Loading synthetic data ...")
    results = load_synthetic_data(conn, force_reload=True)
    print("Load complete:")
    for t, c in results.items():
        print(f"  {t}: {c} rows")
print("DONE")
