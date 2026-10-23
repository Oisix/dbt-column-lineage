"""Regression guard: Trino's `table(exclude_columns(input => table(x), columns => DESCRIPTOR(c)))`
polymorphic table function is opaque to sqlglot, so a `SELECT *` over it never expands and every
column's lineage stops on a Placeholder. `unwrap_exclude_columns` rewrites it to plain `x`."""
from sqlglot import exp, parse_one
from sqlglot.lineage import lineage

from dbt_column_lineage.lineage import unwrap_exclude_columns

SQL = """
with ranked as (
    select *, row_number() over (partition by id order by updated_at desc) as rn
    from "db"."analytics"."raw_cases"
),
filtered as (select * from ranked where rn = 1),
deduped as (
    select * from table(exclude_columns(input => table(filtered), columns => DESCRIPTOR(rn)))
),
source as (
    select *, row_number() over (partition by id order by id) as rnk
    from (select * from deduped union all select * from deduped)
)
select id as case_id from source
"""
SCHEMA = {"db": {"analytics": {"raw_cases": {"id": "varchar", "updated_at": "timestamp"}}}}


def _leaves(sql):
    node = lineage("case_id", sql, dialect="trino", schema=SCHEMA)
    return [n for n in node.walk() if not n.downstream]


def test_exclude_columns_breaks_lineage_without_unwrap():
    assert all(isinstance(n.expression, exp.Placeholder) for n in _leaves(SQL))


def test_unwrap_exclude_columns_restores_lineage():
    parsed = unwrap_exclude_columns(parse_one(SQL, dialect="trino"))
    leaves = _leaves(parsed)
    assert leaves and all(isinstance(n.expression, exp.Table) and n.expression.name == "raw_cases" for n in leaves)


def _leaves_for(sql, column):
    parsed = unwrap_exclude_columns(parse_one(sql, dialect="trino"))
    node = lineage(column, parsed, dialect="trino", schema=SCHEMA2)
    return {(n.expression.name, n.expression.db) for n in node.walk() if not n.downstream and isinstance(n.expression, exp.Table)}


SCHEMA2 = {"db": {"a": {"raw": {"id": "int", "rn": "int", "name": "text"},
                        "other": {"id": "int", "name": "text"}}}}


def test_qualified_input_and_union_with_narrower_branch():
    # excluded column must not shift UNION ALL positional mapping; db.a.raw must keep its qualifiers
    sql = """
    with d as (select * from table(exclude_columns(input => table(db.a.raw), columns => DESCRIPTOR(rn))))
    select * from (select * from d union all select * from db.a.other)
    """
    for col in ("id", "name"):
        assert _leaves_for(sql, col) == {("raw", "a"), ("other", "a")}


def test_qualified_input_with_same_table_name_in_two_schemas():
    # a bare `raw_cases` would raise SchemaError: Ambiguous mapping (swallowed -> lineage silently lost)
    schema = {"db": {"analytics": {"raw_cases": {"id": "int", "rn": "int"}},
                     "staging": {"raw_cases": {"id": "int", "rn": "int"}}}}
    sql = """select z.id as case_id from (
        select * from table(exclude_columns(input => table("db"."analytics"."raw_cases"), columns => DESCRIPTOR(rn)))
    ) as z"""
    parsed = unwrap_exclude_columns(parse_one(sql, dialect="trino"))
    leaves = [n.expression for n in lineage("case_id", parsed, dialect="trino", schema=schema).walk() if not n.downstream]
    assert [(t.db, t.name) for t in leaves] == [("analytics", "raw_cases")]
