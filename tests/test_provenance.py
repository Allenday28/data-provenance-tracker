"""Tests for the data-provenance-tracker. Run with `pytest -q`."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from provenance import Tracker, tracked


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "customer_id": [1, 1, 2, 2, 3],
            "amount": [50.0, 200.0, 75.0, 120.0, 300.0],
        }
    )


def test_source_registration_creates_source_node():
    t = Tracker()
    df = _sample_df()
    t.register_source("orders.csv", df)
    node = t.node_for(df)
    assert node is not None
    assert node.kind == "source"
    assert node.label == "orders.csv"
    assert node.shape == (5, 2)


def test_tracked_decorator_records_op_and_params():
    t = Tracker()

    @tracked(t, name="filter_high_value")
    def filter_high_value(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
        return df[df["amount"] >= threshold]

    raw = t.register_source("orders", _sample_df())
    big = filter_high_value(raw, threshold=100.0)

    assert len(t.edges) == 1
    edge = t.edges[0]
    assert edge.op == "filter_high_value"
    assert edge.params == {"threshold": 100.0}
    assert len(edge.inputs) == 1
    out = t.node_for(big)
    assert out is not None and out.shape == (3, 2)


def test_chained_ops_build_lineage():
    t = Tracker()

    @tracked(t)
    def filter_big(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
        return df[df["amount"] >= threshold]

    @tracked(t)
    def per_customer(df: pd.DataFrame) -> pd.DataFrame:
        return df.groupby("customer_id", as_index=False)["amount"].sum()

    raw = t.register_source("orders", _sample_df())
    agg = per_customer(filter_big(raw, threshold=100.0))

    assert len(t.edges) == 2
    # The aggregate should have two ancestors: the filtered frame and the source.
    ancestors = t.ancestors(agg)
    labels = {a.label for a in ancestors}
    assert "orders" in labels
    assert any("filter_big" in lbl for lbl in labels)


def test_to_json_roundtrips(tmp_path: Path):
    t = Tracker()

    @tracked(t, name="double")
    def double(df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["amount"] = out["amount"] * 2
        return out

    raw = t.register_source("src", _sample_df())
    double(raw)

    path = tmp_path / "lineage.json"
    t.to_json(str(path))
    data = json.loads(path.read_text())
    assert "nodes" in data and "edges" in data
    assert len(data["nodes"]) == 2
    assert data["edges"][0]["op"] == "double"


def test_to_dot_contains_edges(tmp_path: Path):
    t = Tracker()

    @tracked(t, name="identity")
    def identity(df: pd.DataFrame) -> pd.DataFrame:
        return df.copy()

    raw = t.register_source("raw", _sample_df())
    identity(raw)

    path = tmp_path / "lineage.dot"
    t.to_dot(str(path))
    text = path.read_text()
    assert "digraph provenance" in text
    assert "identity" in text


def test_non_dataframe_return_raises():
    t = Tracker()

    @tracked(t)
    def broken(df: pd.DataFrame) -> int:  # type: ignore[return-value]
        return 42

    raw = t.register_source("r", _sample_df())
    try:
        broken(raw)
    except TypeError as e:
        assert "DataFrame" in str(e)
    else:
        raise AssertionError("expected TypeError")
