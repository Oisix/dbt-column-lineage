"""Tests for the CTE-only label guard (`__is_cte_only_label`).

A lineage leaf can resolve to a CTE rather than a real table. `DbtSqlglot`
drops such labels so no node is drawn for a relation that does not exist —
but only when they are CTE names that are NOT also real dbt objects (dbt
frequently wraps a ref in a same-named CTE, e.g.
`with dim_calendar as (select * from {{ ref('dim_calendar') }})`).

Two paths reach the guard:
- `__resolve_star_select_label` walks a star-select's FROM and returns its
  name; a CTE reference is an `exp.Table` in sqlglot's AST, so a FROM over a
  CTE yields the CTE name. Independent of the sqlglot version.
- sqlglot used to return an UNPIVOT's input CTE as a table leaf
  (sqlglot#7727). Fixed in 30.11.0, which `pyproject` now requires, so this
  path no longer fires — the guard is kept for the first one.
"""
from sqlglot import parse_one


def _cte_names(dbt, sql):
    return dbt._DbtSqlglot__cte_names(parse_one(sql, dialect="snowflake"))


def _is_cte_only(dbt, label, cte_names):
    return dbt._DbtSqlglot__is_cte_only_label(label, cte_names, "src")


# --- pure-ish helper units -------------------------------------------------

def test_cte_names_collects_aliases(dbt):
    sql = "with a as (select 1), b as (select 2) select * from a join b"
    assert _cte_names(dbt, sql) == {"a", "b"}


def test_cte_names_empty_when_no_cte(dbt):
    assert _cte_names(dbt, "select 1 from t") == set()


def test_real_dbt_object_names_includes_models(dbt):
    names = dbt._DbtSqlglot__real_dbt_object_names()
    assert "base_model" in names
    assert "child_model" in names


def test_cte_only_when_cte_and_not_real_object(dbt):
    # CTE 名 かつ 実在 dbt オブジェクトでない → 除外
    assert _is_cte_only(dbt, "weekly_summary_item_str", {"weekly_summary_item_str"}) is True


def test_not_cte_only_when_real_object_even_if_cte(dbt):
    # 実在モデル名と同名の CTE(ref ラップ)は残す
    assert _is_cte_only(dbt, "base_model", {"base_model"}) is False


def test_not_cte_only_when_not_a_cte(dbt):
    # CTE 名でなければ(実テーブル/未宣言の raw テーブル等)残す
    assert _is_cte_only(dbt, "some_raw_table", {"src"}) is False


def test_cte_only_label_is_case_insensitive(dbt):
    assert _is_cte_only(dbt, "SRC", {"src"}) is True


def test_star_select_from_cte_resolves_to_cte_name(dbt):
    # ガードを残す理由そのもの: star-select の FROM が CTE だと、CTE 名が
    # ラベルとして返る(sqlglot の AST では CTE 参照も exp.Table)。
    # ガードを外すとこれがテーブルノードとして描かれてしまう。
    parsed = parse_one(
        "select *, row_number() over (partition by id order by ts desc) as rn from some_cte",
        dialect="snowflake",
    )
    assert dbt._DbtSqlglot__resolve_star_select_label(parsed) == "some_cte"
    assert _is_cte_only(dbt, "some_cte", {"some_cte"}) is True


# --- end-to-end through column_lineage ------------------------------------

def test_forward_unpivot_score_excludes_input_cte(dbt):
    # child_model.score は UNPIVOT 由来。入力 CTE `src` はテーブルではないので
    # ノードに現れない(sqlglot 30.11+ ではそもそも末端として漏れない)。
    dbt.column_lineage("child_model", "SCORE", False)
    names = {n["data"]["name"] for n in dbt.ret_edges_nodes()["nodes"]}
    assert "src" not in names
    assert "child_model" in names


def test_forward_plain_model_traces_to_base_model(dbt):
    # UNPIVOT を含まない plain_model は実上流 base_model まで辿れる(ガードは実テーブルを落とさない)。
    dbt.column_lineage("plain_model", "ID", False)
    names = {n["data"]["name"] for n in dbt.ret_edges_nodes()["nodes"]}
    assert "base_model" in names
    assert "plain_model" in names


# --- /cte page must NOT be affected by the guard ---------------------------

def test_cte_page_still_shows_unpivot_input_cte(dbt):
    # ガードは共有関数 __get_sqlglot_lineage に入っているが、/cte ページ
    # (cte_dependency) は CTE を表示するのが目的。CTE ノードは生パースから作られ、
    # 除外済み labels は __cte_dependency_impl 内の未使用変数にしか流れないため、
    # UNPIVOT 入力 CTE `src` も /cte 上では従来どおり表示される。
    res = dbt.cte_dependency("child_model", ["SCORE"])
    cte_ids = {n["id"] for n in res["nodes"] if n.get("type") == "cte"}
    assert "src" in cte_ids
