"""End-to-end example: track a 3-step pandas pipeline and export its lineage.

Run:
    python examples/run_example.py

Outputs `provenance.json` and `provenance.dot` in the current directory.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make `src/` importable when running from the project root.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402

from provenance import Tracker, tracked  # noqa: E402
from provenance.graph import to_text_summary  # noqa: E402


def main() -> int:
    tracker = Tracker()

    @tracked(tracker, name="filter_high_value")
    def filter_high_value(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
        return df[df["amount"] >= threshold].reset_index(drop=True)

    @tracked(tracker, name="per_customer_total")
    def per_customer_total(df: pd.DataFrame) -> pd.DataFrame:
        return df.groupby("customer_id", as_index=False)["amount"].sum()

    @tracked(tracker, name="rank_customers")
    def rank_customers(df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["rank"] = out["amount"].rank(ascending=False, method="dense").astype(int)
        return out.sort_values("rank").reset_index(drop=True)

    raw = tracker.register_source(
        "orders.csv",
        pd.DataFrame(
            {
                "customer_id": [1, 1, 2, 2, 3, 3, 3],
                "amount": [50.0, 200.0, 75.0, 120.0, 300.0, 250.0, 80.0],
            }
        ),
    )

    big = filter_high_value(raw, threshold=100.0)
    agg = per_customer_total(big)
    ranked = rank_customers(agg)

    tracker.to_json("provenance.json")
    tracker.to_dot("provenance.dot")

    print("=== Final result ===")
    print(ranked)
    print()
    print("=== Lineage ===")
    print(to_text_summary(tracker))
    print()
    print("Wrote provenance.json and provenance.dot")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
