"""Optimize a SQL query with n joins, for drperf.

Usage: run_sqlglot.py [n_joins=N]

The region is one `sqlglot.optimizer.optimize` call. States are the join count and
its square: the optimizer performs a number of full expression walks proportional
to the join count, over an expression whose size is also proportional to it, so no
plane in the join count alone can express the cost.
"""
import sys

sys.path.insert(0, "/home/ubuntu/drperf/perfmark/python")
import perfmark


def main():
    args = {}
    for a in sys.argv[1:]:
        if "=" in a:
            k, v = a.split("=", 1)
            args[k] = int(v)
    n = args.get("n_joins", 40)

    import sqlglot
    from sqlglot.optimizer import optimize

    joins = " ".join(f"JOIN t{i} ON t{i}.id = t0.id" for i in range(1, n))
    sql = f"SELECT * FROM t0 {joins}"
    schema = {f"t{i}": {"id": "INT", "v": "INT"} for i in range(n)}
    expression = sqlglot.parse_one(sql)

    with perfmark.region("optimize", n_joins=n, n_joins_sq=n * n):
        result = optimize(expression, schema=schema)

    print(f"n_joins={n} output_columns={len(result.expressions)}")


if __name__ == "__main__":
    main()
