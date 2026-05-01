from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from quant_engine.config import OptimizationRequest, WalkForwardRequest
from quant_engine.data.cache import get_ohlcv
from quant_engine.optimize.grid import run_grid_optimization
from quant_engine.runner import run_backtest


def parse_duration(value: str) -> timedelta:
    text = value.strip().lower()
    if len(text) < 2:
        raise ValueError("duration must include a unit, e.g. 180d")
    amount = int(text[:-1])
    unit = text[-1]
    if amount <= 0:
        raise ValueError("duration amount must be positive")
    if unit == "d":
        return timedelta(days=amount)
    if unit == "w":
        return timedelta(weeks=amount)
    if unit == "m":
        return timedelta(days=amount * 30)
    if unit == "y":
        return timedelta(days=amount * 365)
    raise ValueError("duration unit must be one of d, w, m, y")


def build_windows(
    index: pd.DatetimeIndex, train_window: timedelta, test_window: timedelta
) -> list[dict[str, pd.Timestamp]]:
    if index.empty:
        return []
    start = pd.Timestamp(index.min())
    final = pd.Timestamp(index.max())
    windows: list[dict[str, pd.Timestamp]] = []
    train_start = start
    while train_start + train_window + test_window <= final:
        train_end = train_start + train_window
        test_end = train_end + test_window
        windows.append(
            {
                "train_start": train_start,
                "train_end": train_end,
                "test_start": train_end,
                "test_end": test_end,
            }
        )
        train_start = train_start + test_window
    return windows


def run_walkforward(
    request: WalkForwardRequest,
    data: pd.DataFrame | None = None,
    *,
    write_outputs: bool = True,
) -> pd.DataFrame:
    frame = data if data is not None else get_ohlcv(request.backtest.data)
    windows = build_windows(frame.index, request.train_window, request.test_window)
    if not windows:
        raise ValueError("not enough data for requested train/test windows")

    rows: list[dict[str, Any]] = []
    for number, window in enumerate(windows, start=1):
        train = frame.loc[window["train_start"] : window["train_end"]]
        test = frame.loc[window["test_start"] : window["test_end"]]
        if train.empty or test.empty:
            continue

        opt_request = OptimizationRequest(
            backtest=request.backtest,
            params=request.params,
            metric=request.metric,
            top_n=1,
            results_dir=request.results_dir,
        )
        optimization = run_grid_optimization(opt_request, data=train, write_outputs=False)
        best = optimization.iloc[0].to_dict()
        best_params = {name: best[name] for name in request.params}
        test_backtest = request.backtest.model_copy(
            update={"strategy_params": best_params, "run_id": None}
        )
        test_result = run_backtest(
            test_backtest, data=test, write_outputs=False, include_benchmark=True
        )
        rows.append(
            {
                "window": number,
                "train_start": window["train_start"].isoformat(),
                "train_end": window["train_end"].isoformat(),
                "test_start": window["test_start"].isoformat(),
                "test_end": window["test_end"].isoformat(),
                **{f"param_{key}": value for key, value in best_params.items()},
                f"train_{request.metric}": best[request.metric],
                "test_total_return_pct": test_result.stats["total_return_pct"],
                "test_sharpe": test_result.stats["sharpe"],
                "test_max_drawdown_pct": test_result.stats["max_drawdown_pct"],
                "test_closed_trades": test_result.stats["closed_trades"],
            }
        )

    results = pd.DataFrame(rows)
    if results.empty:
        raise ValueError("walk-forward produced no scored windows")

    if write_outputs:
        output_dir = _walkforward_dir(request)
        output_dir.mkdir(parents=True, exist_ok=True)
        results.to_csv(output_dir / "walkforward_results.csv", index=False)
        summary = _summary(results)
        (output_dir / "walkforward_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return results


def _summary(results: pd.DataFrame) -> dict[str, Any]:
    return {
        "windows": int(len(results)),
        "mean_test_total_return_pct": float(results["test_total_return_pct"].mean()),
        "mean_test_sharpe": float(results["test_sharpe"].mean()),
        "worst_test_drawdown_pct": float(results["test_max_drawdown_pct"].min()),
        "total_closed_trades": int(results["test_closed_trades"].sum()),
    }


def _walkforward_dir(request: WalkForwardRequest) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return (
        request.results_dir
        / f"{timestamp}_walkforward_{request.backtest.strategy}_{request.backtest.data.symbol}"
    )
