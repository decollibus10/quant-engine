from __future__ import annotations

from pathlib import Path

import pandas as pd


def daily_returns(equity_curve: pd.DataFrame) -> pd.Series:
    if equity_curve.empty:
        return pd.Series(dtype="float64")
    values = equity_curve["value"].copy()
    if not isinstance(values.index, pd.DatetimeIndex):
        values.index = pd.to_datetime(values.index)
    daily_values = values.resample("1D").last().dropna()
    return daily_values.pct_change().dropna()


def write_tearsheet(equity_curve: pd.DataFrame, output_path: Path, title: str) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    returns = daily_returns(equity_curve)
    if returns.empty:
        output_path.write_text(
            f"<html><body><h1>{title}</h1><p>Not enough data for a tear sheet.</p></body></html>",
            encoding="utf-8",
        )
        return output_path

    try:
        import quantstats as qs

        qs.reports.html(returns, output=str(output_path), title=title)
    except Exception as exc:  # pragma: no cover - defensive fallback for quantstats drift
        output_path.write_text(
            (
                f"<html><body><h1>{title}</h1>"
                f"<p>quantstats report failed: {exc}</p>"
                f"<p>Total daily observations: {len(returns)}</p></body></html>"
            ),
            encoding="utf-8",
        )
    return output_path
