"""CLI: `python -m provenance show <lineage.json>`

Reads a lineage JSON previously written by Tracker.to_json() and prints a
readable summary of the ops that produced the final dataset.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="provenance",
        description="Inspect a data lineage JSON file.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    show = sub.add_parser("show", help="Print a readable summary of a lineage file.")
    show.add_argument("file", help="Path to a lineage JSON file.")

    args = parser.parse_args(argv)

    if args.cmd == "show":
        data = json.loads(Path(args.file).read_text())
        nodes = {n["id"]: n for n in data["nodes"]}
        edges = data["edges"]
        print(f"Nodes: {len(nodes)}  Edges: {len(edges)}\n")
        for edge in edges:
            out = nodes[edge["output"]]
            inputs = ", ".join(
                f"{nodes[i]['label']}[{nodes[i]['shape'][0]}x{nodes[i]['shape'][1]}]"
                for i in edge["inputs"]
            )
            params = (
                ", ".join(f"{k}={v}" for k, v in edge.get("params", {}).items())
            )
            suffix = f"  ({params})" if params else ""
            print(
                f"{edge['op']}: {inputs} -> "
                f"{out['label']}[{out['shape'][0]}x{out['shape'][1]}]{suffix}"
            )
        return 0
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
