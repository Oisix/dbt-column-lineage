"""Regression guard for a column whose lineage passes through a
`SELECT *, ROW_NUMBER() OVER (...) FROM x` dedup subquery (a common
"latest row per key" pattern).

sqlglot's lineage() correctly walks into the expression and finds the raw
source columns, but the terminal node it lands on is the dedup subquery's
own `Select` (the wildcard projection), not an `exp.Table`. `DbtSqlglot`
only ever recorded a label when the leaf node's expression was `exp.Table`,
so this case silently produced an empty `labels` set — no upstream box, no
edge — even though the columns were correctly identified.

Trigger condition observed against a real production project: `__get_sqlglot_db_schema`
registers each dependency's catalog/schema/table with `.upper()`, while a
locally-compiled (e.g. dbt-duckdb) or case-sensitive-catalog query can
reference the same table via a *quoted lowercase* 3-part identifier. Quoted
identifiers are case-sensitive to sqlglot, so the schema lookup misses, `*`
never expands, and the walk stops on the `Select` itself instead of reaching
the underlying `Table`. Manually verified fixed (edges: [] -> 3 edges,
node added) against a real project's manifest.json/catalog.json.

`__resolve_star_select_label` unwraps such a leaf `Select` (through nested
`Subquery`s) back to its own `FROM` table, so a label still gets attached.
"""
from sqlglot import exp
from sqlglot.lineage import lineage


DEDUP_SQL = """
with deduped as (
    select *, row_number() over (partition by doctor_id order by updated_at desc) as rn
    from "db"."analytics"."raw_doctors"
),
picked as (
    select * from deduped where rn = 1
),
final as (
    select
        picked.doctor_id as doctor_id,
        concat(picked.user_first_name, ' ', picked.user_last_name) as doctor_name
    from picked
)
select * from final
"""


def test_sqlglot_leaf_is_select_not_table():
    # Control case: without this, the bug wouldn't reproduce at all. This is
    # sqlglot's own raw behavior — with no schema given, a wildcard + window
    # function combination terminates on Select, not Table. dbt_column_lineage
    # doesn't pass a schema for internal CTEs either, so production hits the
    # same path.
    node = lineage("doctor_name", DEDUP_SQL, dialect="trino")
    leaves = [n for n in node.walk() if not n.downstream]
    assert leaves, "expected at least one leaf node"
    assert all(isinstance(n.expression, exp.Select) for n in leaves), (
        f"expected sqlglot to terminate on a Select (star + window function) leaf, "
        f"got {[type(n.expression).__name__ for n in leaves]}"
    )


def test_star_select_label_resolves_to_underlying_table(dbt):
    # __resolve_star_select_label expects a single Select node's expression, not the
    # lineage Node wrapper — exercise it the same way __extract_lineage_node does,
    # via the leaf node's own `.expression`.
    node = lineage("doctor_name", DEDUP_SQL, dialect="trino")
    leaf = next(n for n in node.walk() if not n.downstream)
    label = dbt._DbtSqlglot__resolve_star_select_label(leaf.expression)
    # Same convention as the existing Table branch: a quoted identifier is
    # f-string'd as-is, so the label keeps its double quotes (e.g.
    # `"int_dim_patient"` — observed in the same form in production logs).
    assert label and label.strip('"').lower() == "raw_doctors", label
