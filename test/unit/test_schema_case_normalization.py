"""End-to-end guard for identifier-case handling between the sqlglot schema built
from manifest/catalog and the table references in each model's `compiled_code`.

Background (issue #90 / PR #92): `__get_depends_on_table_info` used to register
every dependency as an upper-cased `exp.Table` into `MappingSchema(normalize=False)`.
That only lines up with Snowflake-style unquoted identifiers. On dialects whose
unquoted identifiers normalize to lowercase (trino, duckdb, postgres, ...) the
schema lookup missed for *every* model, so:

- `select id, jan from db.analytics.base_model` -> no upstream at all (0 edges)
- `select * from db.analytics.base_model`        -> no upstream at all
- `select * from a join b` through a CTE          -> an extra empty node for the
  table sqlglot could not attribute the column to

PR #92's `__resolve_star_select_label` fallback papered over the dedup pattern
only. The schema is now built with `normalize=True` and the manifest's original
case, so both sides are normalized by the same dialect rules and the lineage
resolves through `DbtSqlglot.column_lineage`, i.e. the real request path.
"""
import json
import logging
import shutil
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"

BASE = "db.analytics.base_model"        # id, jan, feb
PLAIN = "db.analytics.plain_model"      # id, jan

# (compiled_code, traced column) — every shape must resolve `feb`/`jan` to base_model only.
SHAPES = {
    "unqualified": (f"select id, jan from {BASE}", "jan"),
    "top_star": (f"select * from {BASE}", "jan"),
    "join_unqualified": (f"select jan, feb from {BASE} b join {PLAIN} p on b.id = p.id", "feb"),
    "star_join_cte": (
        f"with d as (select * from {PLAIN} p join {BASE} b on p.id = b.id) select d.feb as feb from d",
        "feb",
    ),
    "dedup": (
        f"with d as (select *, row_number() over (partition by id order by jan desc) as rn from {BASE}) "
        "select d.feb as feb from d where rn = 1",
        "feb",
    ),
}


def _project_with_model(tmp_path: Path, compiled_code: str, column: str) -> Path:
    """fixtures をコピーし、base_model/plain_model に依存するモデル `m` を足した
    dbt プロジェクトディレクトリを返す(元 fixture は他テストの前提なので触らない)。"""
    project = tmp_path / "project"
    shutil.copytree(FIXTURE_DIR, project)
    target = project / "target"
    manifest = json.loads((target / "manifest.json").read_text())
    catalog = json.loads((target / "catalog.json").read_text())

    uid = "model.test_proj.m"
    manifest["nodes"][uid] = {
        "resource_type": "model",
        "name": "m",
        "unique_id": uid,
        "database": "db",
        "schema": "analytics",
        "config": {"materialized": "view"},
        "depends_on": {"nodes": ["model.test_proj.base_model", "model.test_proj.plain_model"]},
        "columns": {column: {"name": column, "type": "INT"}},
        "compiled_code": compiled_code,
    }
    manifest["parent_map"][uid] = ["model.test_proj.base_model", "model.test_proj.plain_model"]
    manifest["child_map"][uid] = []
    catalog["nodes"][uid] = {"columns": {column.upper(): {"name": column.upper(), "type": "INT"}}}
    (target / "manifest.json").write_text(json.dumps(manifest))
    (target / "catalog.json").write_text(json.dumps(catalog))
    return project


@pytest.mark.parametrize("dialect", ["snowflake", "trino"])
@pytest.mark.parametrize("shape", list(SHAPES))
def test_column_lineage_resolves_upstream(monkeypatch, tmp_path, dialect, shape):
    compiled_code, column = SHAPES[shape]
    monkeypatch.setenv("DBT_PROJECT_DIR", str(_project_with_model(tmp_path, compiled_code, column)))
    from dbt_column_lineage.lineage import DbtSqlglot

    DbtSqlglot._instance = None
    try:
        dbt = DbtSqlglot(logging.getLogger("test"), request_depth=-1)
        # SQLGLOT_DIALECT はモジュール定数(import 時に確定)なのでインスタンス側を差し替える
        dbt.dialect = dialect
        dbt.column_lineage("m", column, False)
        result = dbt.ret_edges_nodes()
    finally:
        DbtSqlglot._instance = None

    upstream = {n["data"]["name"]: list(n["data"]["columns"])
                for n in result["nodes"] if n["data"]["name"] != "m"}
    # base_model だけに繋がり(取りこぼしも、列を割り当てられない空ノードもなし)、
    # その列は追跡対象の1列に解決される
    assert set(upstream) == {"base_model"}, upstream
    assert [c.lower() for c in upstream["base_model"]] == [column], upstream
    assert len(result["edges"]) == 1, result["edges"]
