"""Characterization tests for the lineage walk shared by both column-lineage paths.

`__get_sqlglot_lineage` (forward / per-column) and `__build_reverse_index`
(reverse / batch) both delegate the node walk to `__extract_lineage_node`.
Consolidating them means an edit to that helper now moves forward lineage too,
so these tests pin the forward path's output on the SQL shapes that actually
exercise the helper's interesting branches:

- `star_select_over_cte`  → `__resolve_star_select_label` (the leaf is a Select,
  not a Table, so the label comes from walking its FROM)
- `cte_only_label`        → `__is_cte_only_label` (a CTE that is not a real dbt
  object must not become a node)
- `unpivot`               → sqlglot's UNPIVOT fan-out (one output column drawing
  on several input columns)
- `join_two_tables`       → two different source tables in one model
- `union_all`             → one column with two upstream branches
- `expr_and_agg`          → aggregates/expressions, incl. `count(*)` which has no
  upstream column at all
- `nonexistent_column`    → a requested column that does not exist is dropped

The expected values were captured from the implementation before the walk was
consolidated (PR #119) and verified byte-identical across that change, so a
diff here means behavior moved, not that the baseline was guessed.

The demo project used for the before/after sweep does not reach any of these
branches — that is exactly why they are pinned here.
"""
import pytest
from sqlglot import parse_one
from sqlglot.schema import MappingSchema

DIALECT = "snowflake"


@pytest.fixture
def schema():
    s = MappingSchema(dialect=DIALECT, normalize=True)
    s.add_table(
        "raw_db.raw_schema.orders",
        column_mapping={
            "id": "NUMBER", "amount": "NUMBER", "country": "STRING",
            "q1": "NUMBER", "q2": "NUMBER",
        },
    )
    s.add_table(
        "raw_db.raw_schema.customers",
        column_mapping={"id": "NUMBER", "name": "STRING", "country": "STRING"},
    )
    return s


def _forward(dbt, sql, columns, schema, need_meta=False):
    parsed = parse_one(sql, dialect=DIALECT)
    got = dbt._DbtSqlglot__get_sqlglot_lineage(
        "m", parsed, list(columns), schema, need_meta=need_meta
    )
    # labels / columns are list(set) — compare as sets, not sequences
    return {
        column: {"labels": sorted(item["labels"]), "columns": sorted(item["columns"])}
        for column, item in got.items()
    }


# (id, sql, requested columns, expected {column: {labels, columns}})
CASES = [
    (
        "star_select_over_cte",
        "with src as (select * from raw_db.raw_schema.orders) select * from src",
        ["id", "amount", "country"],
        {
            "ID": {"labels": ["ORDERS"], "columns": ["ID"]},
            "AMOUNT": {"labels": ["ORDERS"], "columns": ["AMOUNT"]},
            "COUNTRY": {"labels": ["ORDERS"], "columns": ["COUNTRY"]},
        },
    ),
    (
        "cte_only_label",
        """with helper as (select id, amount from raw_db.raw_schema.orders),
                final as (select id, amount from helper)
           select id, amount from final""",
        ["id", "amount"],
        {
            # helper / final は CTE なのでラベルにならない(__is_cte_only_label)
            "ID": {"labels": ["ORDERS"], "columns": ["ID"]},
            "AMOUNT": {"labels": ["ORDERS"], "columns": ["AMOUNT"]},
        },
    ),
    (
        "unpivot",
        """with base as (select id, q1, q2 from raw_db.raw_schema.orders)
           select id, quarter, val from base unpivot (val for quarter in (q1, q2))""",
        ["id", "quarter", "val"],
        {
            "ID": {"labels": ["ORDERS"], "columns": ["ID"]},
            "QUARTER": {"labels": ["ORDERS"], "columns": ["Q1", "Q2", "QUARTER"]},
            "VAL": {"labels": ["ORDERS"], "columns": ["Q1", "Q2", "VAL"]},
        },
    ),
    (
        "join_two_tables",
        """select o.id as oid, c.name as cname, o.amount as amt
           from raw_db.raw_schema.orders o
           join raw_db.raw_schema.customers c on o.id = c.id""",
        ["oid", "cname", "amt"],
        {
            "OID": {"labels": ["ORDERS"], "columns": ["ID"]},
            "CNAME": {"labels": ["CUSTOMERS"], "columns": ["NAME"]},
            "AMT": {"labels": ["ORDERS"], "columns": ["AMOUNT"]},
        },
    ),
    (
        "union_all",
        """select id, amount from raw_db.raw_schema.orders
           union all
           select id, amount from raw_db.raw_schema.orders""",
        ["id", "amount"],
        {
            "ID": {"labels": ["ORDERS"], "columns": ["ID"]},
            "AMOUNT": {"labels": ["ORDERS"], "columns": ["AMOUNT"]},
        },
    ),
    (
        "expr_and_agg",
        """select country, sum(amount) as total, count(*) as cnt, amount * 2 as doubled
           from raw_db.raw_schema.orders group by country, amount""",
        ["country", "total", "cnt", "doubled"],
        {
            "COUNTRY": {"labels": ["ORDERS"], "columns": ["COUNTRY"]},
            "TOTAL": {"labels": ["ORDERS"], "columns": ["AMOUNT"]},
            "DOUBLED": {"labels": ["ORDERS"], "columns": ["AMOUNT"]},
            # count(*) は上流カラムを持たないので空
            "CNT": {"labels": [], "columns": []},
        },
    ),
    (
        "deep_cte_chain",
        """with a as (select id, amount from raw_db.raw_schema.orders),
                b as (select id as i2, amount as a2 from a),
                c as (select i2 as i3, a2 as a3 from b)
           select i3, a3 from c""",
        ["i3", "a3"],
        {
            "I3": {"labels": ["ORDERS"], "columns": ["I2", "I3", "ID"]},
            "A3": {"labels": ["ORDERS"], "columns": ["A2", "A3", "AMOUNT"]},
        },
    ),
]


@pytest.mark.parametrize("name, sql, columns, expected", CASES, ids=[c[0] for c in CASES])
def test_forward_walk_output_is_pinned(dbt, schema, name, sql, columns, expected):
    assert _forward(dbt, sql, columns, schema) == expected


def test_missing_column_is_dropped_not_faked(dbt, schema):
    """存在しないカラムは結果から落ちる(空エントリを作らない)。"""
    got = _forward(dbt, "select id from raw_db.raw_schema.orders", ["id", "nope"], schema)
    assert sorted(got) == ["ID"]


@pytest.mark.parametrize("name, sql, columns, expected", CASES, ids=[c[0] for c in CASES])
def test_need_meta_does_not_change_labels_or_columns(dbt, schema, name, sql, columns, expected):
    """need_meta=True(/cte 経路)でも labels/columns 部分は同じ。"""
    with_meta = _forward(dbt, sql, columns, schema, need_meta=True)
    assert with_meta == expected
