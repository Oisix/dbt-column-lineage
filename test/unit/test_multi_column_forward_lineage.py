"""Regression tests for issue #117 — forward lineage dropped every column
after the first.

`__get_sqlglot_lineage` loops over `columns` and calls sqlglot's `lineage()`
with the model's parsed SQL. The loop body used to reassign that very
parameter (`parsed_sql = parse_one(cte, ...)`) while collecting replaced
column names, so from the second column on, `lineage()` received the previous
column's *projection* expression instead of the model SELECT. sqlglot then
raised, the handler logged and `continue`d, and the column silently vanished
from the result.

Only the forward path is affected: `__column_lineage_recursive` passes
several columns and no `scope` (the batch/reverse path passes a `scope`, which
makes the expression argument moot, and `/cte` passes a single column).

The trigger is simply **a hop that asks for two or more columns** — no CTE is
required, since the first column's projection alone is enough to clobber the
argument. CTE-heavy models just hit it more often, which is how it was found.

The invariant asserted here: asking for N columns in one call must return the
same thing as asking for each column in its own call.
"""
import logging

import pytest
from sqlglot import parse_one
from sqlglot.schema import MappingSchema

DIALECT = "snowflake"

# 2 段の CTE を重ねたモデル。issue #117 の報告どおり "several CTEs linked
# together" を再現する最小形。
CHAINED_CTE_SQL = """
with base as (
    select id, amount, country from raw_db.raw_schema.orders
),
mid as (
    select id as order_id, amount as amt, country as ctry from base
)
select order_id, amt, ctry from mid
"""


# CTE を一切使わないモデル。CTE チェーンは発症条件ではないことを示す。
FLAT_SQL = "select id, amount, country from raw_db.raw_schema.orders"


@pytest.fixture
def schema():
    s = MappingSchema(dialect=DIALECT, normalize=True)
    s.add_table(
        "raw_db.raw_schema.orders",
        column_mapping={"id": "NUMBER", "amount": "NUMBER", "country": "STRING"},
    )
    return s


def _lineage(dbt, columns, schema, sql=CHAINED_CTE_SQL, need_meta=False):
    # parse_one は呼び出しごとに作り直す(AST が流用されないことを保証するため)
    parsed = parse_one(sql, dialect=DIALECT)
    return dbt._DbtSqlglot__get_sqlglot_lineage(
        "test_model", parsed, list(columns), schema, need_meta=need_meta
    )


def _normalize(result):
    """labels/columns は list(set) で順序が保証されないので、集合比較用に揃える。"""
    return {
        column: {key: sorted(value) for key, value in item.items() if key != "meta"}
        for column, item in result.items()
    }


def test_every_requested_column_is_returned(dbt, schema):
    """複数カラムをまとめて要求しても、全カラムが結果に含まれる。"""
    got = _lineage(dbt, ["order_id", "amt", "ctry"], schema)
    assert sorted(got) == ["AMT", "CTRY", "ORDER_ID"]


def test_batch_matches_per_column_calls(dbt, schema):
    """まとめ呼び出しと 1 カラムずつの呼び出しで結果が一致する。"""
    columns = ["order_id", "amt", "ctry"]

    one_by_one = {}
    for column in columns:
        one_by_one.update(_lineage(dbt, [column], schema))

    batched = _lineage(dbt, columns, schema)

    assert _normalize(batched) == _normalize(one_by_one)


def test_later_columns_resolve_to_the_real_source_table(dbt, schema):
    """2 カラム目以降もソーステーブルまで辿れている(空で返っていない)。"""
    got = _lineage(dbt, ["order_id", "amt", "ctry"], schema)
    for column in ("ORDER_ID", "AMT", "CTRY"):
        assert got[column]["labels"] == ["ORDERS"], column


def test_argument_expression_is_not_mutated_or_rebound(dbt, schema, caplog):
    """ループが引数の AST を壊さない: 走査後も同じ AST で再実行できる。"""
    parsed = parse_one(CHAINED_CTE_SQL, dialect=DIALECT)
    call = dbt._DbtSqlglot__get_sqlglot_lineage

    with caplog.at_level(logging.ERROR):
        first = call("test_model", parsed, ["order_id", "amt", "ctry"], schema)
        # 同じ AST インスタンスを使い回しても結果が変わらない
        second = call("test_model", parsed, ["order_id", "amt", "ctry"], schema)

    assert first == second
    assert "lineage error" not in caplog.text


def test_flat_select_without_any_cte_also_returns_every_column(dbt, schema):
    """CTE が無くても、2 カラム目以降が落ちないこと(発症条件は複数カラム)。"""
    columns = ["id", "amount", "country"]

    one_by_one = {}
    for column in columns:
        one_by_one.update(_lineage(dbt, [column], schema, sql=FLAT_SQL))
    batched = _lineage(dbt, columns, schema, sql=FLAT_SQL)

    assert sorted(batched) == ["AMOUNT", "COUNTRY", "ID"]
    # labels/columns は list(set) なので、順序ではなく集合として比較する
    assert _normalize(batched) == _normalize(one_by_one)


def test_meta_path_also_survives_multiple_columns(dbt, schema):
    """need_meta=True(/cte 経路と同じ形)でも全カラム分の meta が返る。

    /cte は現状 1 カラムしか渡さないので本番影響はないが、走査処理を
    __extract_lineage_node に統合する際の安全網としてここで固定しておく。"""
    columns = ["order_id", "amt", "ctry"]

    one_by_one = {}
    for column in columns:
        one_by_one.update(_lineage(dbt, [column], schema, need_meta=True))
    batched = _lineage(dbt, columns, schema, need_meta=True)

    assert sorted(batched) == ["AMT", "CTRY", "ORDER_ID"]
    for column in batched:
        assert batched[column]["meta"], f"{column} の meta が空"
        assert batched[column]["meta"] == one_by_one[column]["meta"], column
    assert _normalize(batched) == _normalize(one_by_one)
