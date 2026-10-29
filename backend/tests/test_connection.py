from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.db.connection import import_dataframe


def test_import_dataframe_targets_columns_and_ignores_only_ephemeral_certificate() -> None:
    conn = MagicMock()
    original_execute = conn.execute
    dataframe = pd.DataFrame({"supplier_id": ["S001"], "supplier_name": ["Test"]})
    conn.import_from_pandas.side_effect = (
        lambda frame, table, import_params: conn.execute(
            "IMPORT INTO SUPPLIERS FROM CSV AT 'https://127.0.0.1:1234' FILE '000.gz'"
        )
    )

    import_dataframe(conn, dataframe, "SUPPLIERS")

    conn.import_from_pandas.assert_called_once_with(
        dataframe,
        "SUPPLIERS",
        import_params={"columns": ["supplier_id", "supplier_name"]},
    )
    conn.execute.assert_called_once_with(
        "IMPORT INTO SUPPLIERS FROM CSV AT 'https://127.0.0.1:1234' FILE '000.gz'\n"
        "IGNORE CERTIFICATE"
    )
    assert conn.execute is original_execute


def test_import_dataframe_restores_execute_after_import_failure() -> None:
    conn = MagicMock()
    original_execute = conn.execute
    conn.import_from_pandas.side_effect = RuntimeError("import failed")

    with pytest.raises(RuntimeError, match="import failed"):
        import_dataframe(conn, pd.DataFrame({"supplier_id": ["S001"]}), "SUPPLIERS")

    assert conn.execute is original_execute


def test_import_dataframe_does_not_change_non_https_queries() -> None:
    conn = MagicMock()
    conn.import_from_pandas.side_effect = (
        lambda frame, table, import_params: conn.execute("SELECT 1")
    )

    import_dataframe(conn, pd.DataFrame({"supplier_id": ["S001"]}), "SUPPLIERS")

    conn.execute.assert_called_once_with("SELECT 1")
