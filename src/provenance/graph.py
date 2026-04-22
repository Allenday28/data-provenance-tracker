"""Graph export helpers: Graphviz DOT rendering + readable text summary."""

from __future__ import annotations

from provenance.tracker import Tracker


def to_dot_string(tracker: Tracker) -> str:
    """Render a Tracker's graph as a Graphviz DOT string.

    Source nodes are drawn as boxes; derived datasets as ellipses. Each edge
    carries the op name as its label.
    """
    lines = ["digraph provenance {", '  rankdir=LR;', '  node [fontname="Helvetica"];']

    for node in tracker.nodes.values():
        shape = "box" if node.kind == "source" else "ellipse"
        label = f"{node.label}\\n[{node.shape[0]}x{node.shape[1]}]"
        lines.append(f'  "{node.id}" [label="{label}", shape={shape}];')

    for edge in tracker.edges:
        for src in edge.inputs:
            lines.append(f'  "{src}" -> "{edge.output}" [label="{edge.op}"];')

    lines.append("}")
    return "\n".join(lines)


def to_text_summary(tracker: Tracker) -> str:
    """Produce a human-readable summary of the lineage graph."""
    lines = [f"Nodes: {len(tracker.nodes)}  Edges: {len(tracker.edges)}", ""]
    for edge in tracker.edges:
        out_node = tracker.nodes[edge.output]
        input_labels = ", ".join(
            f"{tracker.nodes[i].label}[{tracker.nodes[i].shape[0]}x{tracker.nodes[i].shape[1]}]"
            for i in edge.inputs
        )
        params = (
            ", ".join(f"{k}={v}" for k, v in edge.params.items())
            if edge.params
            else ""
        )
        suffix = f"  ({params})" if params else ""
        lines.append(
            f"{edge.op}: {input_labels} -> "
            f"{out_node.label}[{out_node.shape[0]}x{out_node.shape[1]}]{suffix}"
        )
    return "\n".join(lines)
