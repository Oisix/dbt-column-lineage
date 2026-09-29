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
