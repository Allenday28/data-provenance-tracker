"""`@tracked` decorator — instrument a DataFrame-producing function so the
tracker records the call in its lineage graph."""

from __future__ import annotations

import functools
import inspect
from typing import Any, Callable

import pandas as pd

from provenance.tracker import Tracker


def tracked(
    tracker: Tracker,
    *,
    name: str | None = None,
) -> Callable[[Callable[..., pd.DataFrame]], Callable[..., pd.DataFrame]]:
    """Return a decorator that records each call into `tracker`.

    - DataFrame arguments (positional or keyword) become inputs.
    - Non-DataFrame arguments become params (stringified for JSON friendliness).
    - The return value (which must be a DataFrame) becomes the output node.
    """

    def decorator(fn: Callable[..., pd.DataFrame]) -> Callable[..., pd.DataFrame]:
        op_name = name or fn.__name__
        sig = inspect.signature(fn)

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> pd.DataFrame:
            result = fn(*args, **kwargs)
            if not isinstance(result, pd.DataFrame):
                raise TypeError(
                    f"@tracked function {op_name!r} must return a DataFrame, "
                    f"got {type(result).__name__}"
                )

            # Map args to parameter names for nicer params output.
            try:
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                items = bound.arguments.items()
            except TypeError:
                items = list(enumerate(args)) + list(kwargs.items())

            inputs: list[pd.DataFrame] = []
            params: dict[str, Any] = {}
            for key, value in items:
                if isinstance(value, pd.DataFrame):
                    inputs.append(value)
                else:
                    params[str(key)] = _safe(value)

            tracker.record(op=op_name, inputs=inputs, output=result, params=params)
            return result

        return wrapper

    return decorator


def _safe(value: Any) -> Any:
    """Coerce a value to something JSON-serializable for params storage."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in value.items()}
    return repr(value)
