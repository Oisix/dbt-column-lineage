"""Tests for surfacing partial lineage (`warnings` in the API response).

When sqlglot cannot parse a model's compiled SQL, or cannot trace one column,
the affected nodes/edges never make it into the graph — but the request still
returns 200. It used to do so with nothing but an `ERROR` line in the server
log, so an incomplete graph was indistinguishable from a complete one. That is
what kept issue #117 hidden for so long.

`ret_edges_nodes()` now carries a `warnings` list alongside `truncated`.
`truncated` stays reserved for the `MAX_LINEAGE_SECONDS` budget cut; these are
a different failure and get their own field.

The reverse path needs particular care: `__build_reverse_index` caches its
per-source index for the life of the process, so a warning that was only
recorded while building it would vanish on every later request for the same
source — which would be the same silent-incompleteness bug in a new place.
"""
import json
import logging
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def broken_project(tmp_path, monkeypatch):
    """fixtures をコピーし、1 モデルの compiled_code を sqlglot が解析できない
    文字列に差し替えた dbt プロジェクトを用意する。"""
    target = tmp_path / "target"
    target.mkdir()
    manifest = json.loads((FIXTURE_DIR / "target" / "manifest.json").read_text())
    catalog = json.loads((FIXTURE_DIR / "target" / "catalog.json").read_text())

    # 親を持つ(= forward で辿られる)モデルを 1 つ壊す
    broken_id = next(
        uid for uid, node in manifest["nodes"].items()
        if node.get("resource_type") == "model"
        and manifest.get("parent_map", {}).get(uid)
    )
    manifest["nodes"][broken_id]["compiled_code"] = "this is not valid sql ((("

    (target / "manifest.json").write_text(json.dumps(manifest))
    (target / "catalog.json").write_text(json.dumps(catalog))
    monkeypatch.setenv("DBT_PROJECT_DIR", str(tmp_path))

    from dbt_column_lineage.lineage import DbtSqlglot
    DbtSqlglot._instance = None
    yield DbtSqlglot, manifest["nodes"][broken_id]["name"], manifest, catalog
    DbtSqlglot._instance = None


def _fresh(DbtSqlglot):
    DbtSqlglot._instance = None
    return DbtSqlglot(logging.getLogger("warn"), request_depth=-1)


# --- clean projects stay clean --------------------------------------------

def test_healthy_lineage_reports_no_warnings(dbt):
    """解析できるモデルだけなら warnings は空(バナーを出さない)。"""
    dbt.column_lineage("child_model", "SCORE", False)
    assert dbt.ret_edges_nodes()["warnings"] == []


def test_response_always_carries_the_field(dbt):
    """キーは常に存在する(フロントが undefined を見ないで済む)。"""
    dbt.column_lineage("child_model", "SCORE", False)
    assert "warnings" in dbt.ret_edges_nodes()


def test_warnings_reset_between_requests(dbt):
    """warnings は per-request。前のリクエストの警告が漏れない。"""
    dbt.lineage_warnings.append({"kind": "model_parse", "source": "stale", "message": "x"})
    from dbt_column_lineage.lineage import DbtSqlglot
    fresh = DbtSqlglot(logging.getLogger("warn"), request_depth=-1)
    assert fresh.ret_edges_nodes()["warnings"] == []


# --- a model sqlglot cannot parse is reported, not swallowed ---------------

def test_unparseable_model_is_reported(broken_project):
    DbtSqlglot, broken_name, manifest, _ = broken_project
    d = _fresh(DbtSqlglot)
    # 壊したモデル自身を起点に forward を引く
    d.column_lineage(broken_name, "SCORE", False)
    warnings = d.ret_edges_nodes()["warnings"]

    assert warnings, "解析できないモデルがあるのに warnings が空"
    assert any(w["kind"] == "model_parse" for w in warnings), warnings
    assert any(broken_name == w["source"] for w in warnings), warnings


def test_warning_does_not_set_truncated(broken_project):
    """truncated は時間予算専用。解析失敗で立ててはいけない。"""
    DbtSqlglot, broken_name, _, _ = broken_project
    d = _fresh(DbtSqlglot)
    d.column_lineage(broken_name, "SCORE", False)
    res = d.ret_edges_nodes()
    assert res["warnings"]
    assert res["truncated"] is False


# --- the reverse index caches; the warning must survive the cache ----------

def test_reverse_warning_survives_the_index_cache(broken_project):
    """同じ source への 2 回目のリバース照会でも警告が消えない。

    __build_reverse_index はプロセス寿命でキャッシュされるため、警告を索引と
    一緒に持ち回らないと 2 回目以降は「同じく不完全なのに警告なし」になる。
    """
    DbtSqlglot, broken_name, manifest, _ = broken_project

    # 壊したモデルの親を source にして、子(=壊れたモデル)を索引に通す
    broken_id = next(uid for uid, n in manifest["nodes"].items()
                     if n.get("name") == broken_name)
    parent_id = manifest["parent_map"][broken_id][0]
    parent_name = manifest["nodes"][parent_id]["name"]
    parent_column = next(iter(manifest["nodes"][parent_id].get("columns", {})), None) or "SCORE"

    d = _fresh(DbtSqlglot)          # 索引を構築する 1 回目
    d.column_lineage(parent_name, parent_column.upper(), True)
    first = d.ret_edges_nodes()["warnings"]

    # 同一プロセス・同一インスタンス系列の 2 回目(索引はキャッシュヒットする)
    second_inst = DbtSqlglot(logging.getLogger("warn"), request_depth=-1)
    second_inst.column_lineage(parent_name, parent_column.upper(), True)
    second = second_inst.ret_edges_nodes()["warnings"]

    assert first, "1回目で警告が出ていない(前提が崩れている)"
    assert second == first, (
        "索引キャッシュのヒット時に警告が消えた — 2回目以降の利用者には"
        f"不完全なグラフが完全なものに見える。1回目={first} 2回目={second}"
    )
