# data-provenance-tracker

Lightweight **data lineage tracking** for pandas workflows. Wrap your transform
functions with a single decorator and the tracker records every step — input
frames, output frame, operation name, parameters, row counts — into a directed
acyclic graph (DAG) you can export as JSON or Graphviz DOT.

Useful when you want to answer questions like *"where did this column come
from?"* or *"which source rows contributed to this output?"* without bolting on
a heavyweight metadata system.

## Features

- `@tracked` decorator — one-line instrumentation for any function that takes
  and returns a `DataFrame`.
- In-memory lineage graph — nodes are dataset snapshots, edges are operations.
- Export to **JSON** (for programmatic use) or **Graphviz DOT** (for rendering
  `provenance.png`).
- CLI: `python -m provenance show <run.json>` prints a readable summary.
- Pure Python + pandas. No database, no server.

## Quick start

Run these commands from the repository root. The packages live in `src/`, so add it to Python’s import path:

```bash
python -m pip install -r requirements.txt
export PYTHONPATH="$PWD/src"
python examples/run_example.py
```

That script builds a tiny pipeline (load → filter → aggregate), writes
`provenance.json` and `provenance.dot`, and prints a summary of the lineage.

To render the DOT file as a PNG:

```bash
dot -Tpng provenance.dot -o provenance.png
```

## Example

```python
import pandas as pd
from provenance import Tracker, tracked

tracker = Tracker()

@tracked(tracker, name="filter_high_value")
def filter_high_value(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    return df[df["amount"] >= threshold]

@tracked(tracker, name="per_customer_total")
def per_customer_total(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby("customer_id", as_index=False)["amount"].sum()

raw = tracker.register_source("orders.csv", pd.read_csv("orders.csv"))
big = filter_high_value(raw, threshold=100.0)
agg = per_customer_total(big)

tracker.to_json("provenance.json")
tracker.to_dot("provenance.dot")
```

## Layout

```
data-provenance-tracker/
├── src/provenance/
│   ├── tracker.py        # Tracker, Node, Edge
│   ├── decorators.py     # @tracked
│   ├── graph.py          # JSON + DOT export
│   └── cli.py            # python -m provenance show
├── tests/test_provenance.py
└── examples/run_example.py
```

## Tech

Python 3.10+ · pandas · stdlib json · pytest.

## License

MIT — see LICENSE.
