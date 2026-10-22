"""Regression guard for sqlglot's UNPIVOT lineage
(https://github.com/tobymao/sqlglot/issues/7727).

Before sqlglot 30.11.0, lineage() did not expand an UNPIVOT's value/name
columns to the columns listed in `IN (...)`; it terminated at the input
relation with a column that does not exist there (a "phantom"). #7727 was
fixed in sqlglot 30.11.0 — this guard originally asserted the broken
behavior and fired on that release; it now asserts the fixed behavior so a
re-regression is caught. `pyproject` requires >=30.11, so it always runs.

`DbtSqlglot`'s `__is_cte_only_label` guard stays, but for an unrelated
reason: `__resolve_star_select_label` can hand back a CTE name. See
`test_cte_label_guard.py`.
"""
from sqlglot import exp
from sqlglot.lineage import lineage


UNPIVOT_SQL = """
WITH src AS (
  SELECT id, jan, feb FROM sales
)
SELECT id, metric_name, score
FROM src UNPIVOT (score FOR metric_name IN (jan, feb))
"""
SCHEMA = {"sales": {"id": "int", "jan": "int", "feb": "int"}}


def _leaf_table_names(col):
    node = lineage(col, UNPIVOT_SQL, schema=SCHEMA, dialect="snowflake")
    return [n.name for n in node.walk()
            if isinstance(n.expression, exp.Table) and not n.downstream]


def test_unpivot_value_column_fans_out_to_sources():
    # sqlglot 30.11.0 (#7727 修正後): score は UNPIVOT の IN (...) に列挙された
    # 元列 sales.jan / sales.feb まで正しく展開される。
    leaves = _leaf_table_names("score")
    assert leaves == ["SALES.JAN", "SALES.FEB"], (
        f"sqlglot UNPIVOT lineage regressed (#7727): got {leaves}."
    )


def test_plain_cte_traces_normally():
    # 対照: UNPIVOT を含まない素の CTE なら sqlglot は実テーブル sales まで辿れる。
    plain_sql = "WITH s AS (SELECT id, jan FROM sales) SELECT id, jan FROM s"
    node = lineage("id", plain_sql, schema={"sales": {"id": "int", "jan": "int"}}, dialect="snowflake")
    leaves = [n.name for n in node.walk()
              if isinstance(n.expression, exp.Table) and not n.downstream]
    assert leaves == ["SALES.ID"], leaves
