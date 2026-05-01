from __future__ import annotations

import itertools
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import matplotlib
import pandas as pd

matplotlib.use("Agg")
from matplotlib import pyplot as plt

from quant_engine.config import OptimizationRequest
from quant_engine.data.cache import get_ohlcv
from quant_engine.runner import run_backtest


def parse_param_grid(expression: str) -> dict[str, list[int | float | str]]:
    grid: dict[str, list[int | float | str]] = {}
    if not expression.strip():
        raise ValueError("params expression cannot be empty")

    for part in expression.split(","):
        name, raw_spec = part.split("=", maxsplit=1)
        key = name.strip()
        if not key:
            raise ValueError("parameter name cannot be empty")
        grid[key] = _parse_values(raw_spec.strip())
    return grid


def run_grid_optimization(
    request: OptimizationRequest,
    data: pd.DataFrame | None = None,
    *,
    write_outputs: bool = True,
) -> pd.DataFrame:
    frame = data if data is not None else get_ohlcv(request.backtest.data)
    rows: list[dict[str, Any]] = []

    for combo in parameter_combinations(request.params):
        backtest = request.backtest.model_copy(update={"strategy_params": combo, "run_id": None})
        result = run_backtest(backtest, data=frame, write_outputs=False, include_benchmark=False)
        rows.append({**combo, **_metric_columns(result.stats)})

    results = pd.DataFrame(rows)
    if results.empty:
        raise ValueError("optimization produced no results")

    metric = request.metric
    if metric not in results.columns:
        raise ValueError(f"metric '{metric}' not found in optimization results")
    results = results.sort_values(metric, ascending=False).reset_index(drop=True)

    if write_outputs:
        output_dir = _optimization_dir(request)
        output_dir.mkdir(parents=True, exist_ok=True)
        results.to_csv(output_dir / "optimization_results.csv", index=False)
        results.head(request.top_n).to_csv(output_dir / "optimization_top.csv", index=False)
        _plot_heatmap(results, request.params, metric, output_dir / "optimization_heatmap.png")

    return results


def parameter_combinations(params: dict[str, list[int | float | str]]) -> list[dict[str, Any]]:
    names = list(params)
    values = [params[name] for name in names]
    return [
        dict(zip(names, combination, strict=True)) for combination in itertools.product(*values)
    ]


def _parse_values(spec: str) -> list[int | float | str]:
    if ".." in spec:
        range_part, _, step_part = spec.partition(":")
        start_raw, end_raw = range_part.split("..", maxsplit=1)
        start = _number(start_raw)
        end = _number(end_raw)
        step = _number(step_part) if step_part else 1
        return cast(list[int | float | str], _inclusive_range(start, end, step))
    if "|" in spec:
        return [_number_or_string(value) for value in spec.split("|")]
    return [_number_or_string(spec)]


def _inclusive_range(start: int | float, end: int | float, step: int | float) -> list[int | float]:
    if step == 0:
        raise ValueError("range step cannot be zero")
    values: list[int | float] = []
    current = start
    if isinstance(start, int) and isinstance(end, int) and isinstance(step, int):
        return list(range(start, end + (1 if step > 0 else -1), step))
    if step > 0:
        while current <= end:
            values.append(round(float(current), 10))
            current = float(current) + float(step)
    else:
        while current >= end:
            values.append(round(float(current), 10))
            current = float(current) + float(step)
    return values


def _number(raw: str) -> int | float:
    text = raw.strip()
    if "." in text:
        return float(text)
    return int(text)


def _number_or_string(raw: str) -> int | float | str:
    text = raw.strip()
    try:
        return _number(text)
    except ValueError:
        return text


def _metric_columns(stats: dict[str, Any]) -> dict[str, Any]:
    return {
        "final_value": stats["final_value"],
        "total_return_pct": stats["total_return_pct"],
        "annual_return_pct": stats["annual_return_pct"],
        "max_drawdown_pct": stats["max_drawdown_pct"],
        "sharpe": stats["sharpe"],
        "closed_trades": stats["closed_trades"],
        "win_rate_pct": stats["win_rate_pct"],
    }


def _optimization_dir(request: OptimizationRequest) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return (
        request.results_dir
        / f"{timestamp}_optimize_{request.backtest.strategy}_{request.backtest.data.symbol}"
    )


def _plot_heatmap(
    results: pd.DataFrame,
    params: dict[str, list[int | float | str]],
    metric: str,
    output_path: Path,
) -> None:
    if len(params) != 2:
        return
    first, second = list(params)
    if not pd.api.types.is_numeric_dtype(results[first]) or not pd.api.types.is_numeric_dtype(
        results[second]
    ):
        return
    pivot = results.pivot_table(index=second, columns=first, values=metric, aggfunc="mean")
    fig, ax = plt.subplots(figsize=(9, 6))
    image = ax.imshow(pivot.values, aspect="auto", origin="lower")
    ax.set_xticks(
        range(len(pivot.columns)), labels=[str(value) for value in pivot.columns], rotation=45
    )
    ax.set_yticks(range(len(pivot.index)), labels=[str(value) for value in pivot.index])
    ax.set_xlabel(first)
    ax.set_ylabel(second)
    ax.set_title(f"{metric} heatmap")
    fig.colorbar(image, ax=ax, label=metric)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
