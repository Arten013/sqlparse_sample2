import os
import sys

import sqlparse

from .hql_tokens import Query

if __name__ == "__main__":
    """お試し用の簡単なCLI"""
    if len(sys.argv) < 2:
        print("File path required as first argument.", file=sys.stderr)
        sys.exit(1)
    path = sys.argv[1]
    if not os.path.exists(path):
        print("File", path, "not found.", file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        for i, root in enumerate(sqlparse.parse(f.read())):
            print("Query", i + 1)
            edges = Query(root).yield_edges()
            for e in edges:
                print(e[0], "->", e[1])
