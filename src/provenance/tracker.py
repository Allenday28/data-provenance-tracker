"""Core lineage graph: Tracker holds Nodes (dataset snapshots) and Edges (ops).

Each DataFrame produced by a tracked function becomes a Node; each function
call becomes an Edge from its inputs to its output. Nodes carry enough
summary metadata (shape, columns, label) to reconstruct a human-readable
lineage without keeping full copies of the data.
"""

from __future__ import annotations

import itertools
import uuid
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class Node:
    """A snapshot of a DataFrame at a point in the pipeline."""

    id: str
    label: str
    shape: tuple[int, int]
    columns: list[str]
    kind: str = "dataset"  # "source" | "dataset"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "shape": list(self.shape),
            "columns": list(self.columns),
            "kind": self.kind,
        }


@dataclass
class Edge:
    """A transform operation linking input nodes to an output node."""

    id: str
    op: str
    params: dict[str, Any]
    inputs: list[str]
    output: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "op": self.op,
            "params": self.params,
            "inputs": list(self.inputs),
            "output": self.output,
        }


class Tracker:
    """Records lineage for a sequence of DataFrame operations.

    Use `register_source(label, df)` to introduce an initial DataFrame and
    `record(op, inputs, output, params)` to record a transform step. The
    `@tracked` decorator (see decorators.py) calls `record` for you.
    """

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        self._df_to_node: dict[int, str] = {}  # id(df) -> node_id
        self._node_counter = itertools.count(1)

    # ------------------------------------------------------------------ #
    # Node/edge registration
    # ------------------------------------------------------------------ #

    def register_source(self, label: str, df: pd.DataFrame) -> pd.DataFrame:
        """Register a source DataFrame so downstream ops can link to it."""
        node = self._make_node(df, label=label, kind="source")
        self._df_to_node[id(df)] = node.id
        return df

    def record(
        self,
        op: str,
        inputs: list[pd.DataFrame],
        output: pd.DataFrame,
        params: dict[str, Any] | None = None,
        label: str | None = None,
    ) -> None:
        """Record one transform: op(name), input frames, output frame, params."""
        input_ids = []
        for frame in inputs:
            node_id = self._df_to_node.get(id(frame))
            if node_id is None:
                # Input wasn't tracked — register it as an auto-detected source.
                auto = self._make_node(frame, label=f"input[{op}]", kind="source")
                self._df_to_node[id(frame)] = auto.id
                node_id = auto.id
            input_ids.append(node_id)

        out_node = self._make_node(output, label=label or op, kind="dataset")
        self._df_to_node[id(output)] = out_node.id

        edge = Edge(
            id=f"e{len(self.edges) + 1}",
            op=op,
            params=dict(params or {}),
            inputs=input_ids,
            output=out_node.id,
        )
        self.edges.append(edge)

    # ------------------------------------------------------------------ #
    # Lookups
    # ------------------------------------------------------------------ #

    def node_for(self, df: pd.DataFrame) -> Node | None:
        """Return the tracker's Node for a given DataFrame, if tracked."""
        node_id = self._df_to_node.get(id(df))
        return self.nodes.get(node_id) if node_id else None

    def ancestors(self, df_or_id: pd.DataFrame | str) -> list[Node]:
        """Return all upstream Nodes that contributed to the given frame/node."""
        node_id = (
            df_or_id
            if isinstance(df_or_id, str)
            else self._df_to_node.get(id(df_or_id))
        )
        if node_id is None or node_id not in self.nodes:
            return []

        # BFS backwards through edges
        edges_by_output: dict[str, Edge] = {e.output: e for e in self.edges}
        seen: set[str] = set()
        stack = [node_id]
        while stack:
            nid = stack.pop()
            if nid in seen:
                continue
            seen.add(nid)
            edge = edges_by_output.get(nid)
            if edge:
                stack.extend(edge.inputs)

        seen.discard(node_id)
        return [self.nodes[n] for n in seen]

    # ------------------------------------------------------------------ #
    # Export
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
        }

    def to_json(self, path: str) -> None:
        """Write the lineage graph to a JSON file."""
        import json

        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    def to_dot(self, path: str) -> None:
        """Write the lineage graph in Graphviz DOT format."""
        from provenance.graph import to_dot_string

        with open(path, "w") as f:
            f.write(to_dot_string(self))

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _make_node(self, df: pd.DataFrame, label: str, kind: str) -> Node:
        node_id = f"n{next(self._node_counter)}_{uuid.uuid4().hex[:6]}"
        node = Node(
            id=node_id,
            label=label,
            shape=(len(df), len(df.columns)),
            columns=list(df.columns),
            kind=kind,
        )
        self.nodes[node_id] = node
        return node
