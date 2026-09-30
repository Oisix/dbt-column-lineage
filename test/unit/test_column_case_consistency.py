"""Regression guard: on lowercase-normalizing dialects (trino, duckdb, ...) the upstream
node's row came back in the SQL's own casing (`jan`), while clicking (+) on that row sends
the column upper-cased (`JAN`) and the backend answers with a row + edges named `JAN`.
The frontend merges node columns case-sensitively, so the same column showed twice.
Every column name the backend emits must use one casing (upper, like the request path)."""
import logging

import pytest

from test_schema_case_normalization import BASE, _project_with_model


def _lineage(source, column, dialect):
    from dbt_column_lineage.lineage import DbtSqlglot

    DbtSqlglot._instance = None
    try:
        dbt = DbtSqlglot(logging.getLogger("test"), request_depth=-1)
        dbt.dialect = dialect
        dbt.column_lineage(source, column, False)
        return dbt.ret_edges_nodes()
    finally:
        DbtSqlglot._instance = None


def _columns(result, name):
    return next(n["data"]["columns"] for n in result["nodes"] if n["data"]["name"] == name)


@pytest.mark.parametrize("dialect", ["snowflake", "trino"])
def test_expanding_upstream_row_keeps_same_column_name(monkeypatch, tmp_path, dialect):
    monkeypatch.setenv("DBT_PROJECT_DIR", str(_project_with_model(tmp_path, f"select id, jan from {BASE}", "jan")))
    first = _lineage("m", "jan", dialect)
    row = _columns(first, "base_model")
    # (+) on that row: the frontend sends the row's own name as the column
    expanded = _lineage("base_model", row[0], dialect)
    assert _columns(expanded, "base_model") == row

    by_id = {n["id"]: n["data"]["columns"] for n in first["nodes"]}
    for e in first["edges"]:
        assert e["sourceHandle"].split("__")[0] in by_id[e["source"]], e
        assert e["targetHandle"].split("__")[0] in by_id[e["target"]], e
