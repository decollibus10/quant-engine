from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from typer.testing import CliRunner

from quant_engine.cli import app
from quant_engine.config import DataRequest
from quant_engine.data.cache import save_cache

runner = CliRunner()


def test_cli_fetch_uses_cached_data(sample_ohlcv: pd.DataFrame, tmp_path: Path) -> None:
    request = DataRequest(
        symbol="SPY",
        start=date(2024, 1, 2),
        end=date(2024, 1, 3),
        timeframe="5Min",
        provider="alpaca",
        cache_dir=tmp_path,
    )
    save_cache(request, sample_ohlcv)

    result = runner.invoke(
        app,
        [
            "fetch",
            "SPY",
            "--from",
            "2024-01-02",
            "--to",
            "2024-01-03",
            "--tf",
            "5Min",
            "--provider",
            "alpaca",
            "--cache-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "SPY" in result.output


def test_cli_backtest_smoke_uses_cached_data(
    sample_ohlcv: pd.DataFrame, tmp_path: Path, monkeypatch
) -> None:
    request = DataRequest(
        symbol="SPY",
        start=date(2024, 1, 2),
        end=date(2024, 1, 3),
        timeframe="5Min",
        provider="alpaca",
        cache_dir=tmp_path / "data",
    )
    save_cache(request, sample_ohlcv)

    def fake_tearsheet(_equity_curve: pd.DataFrame, output_path: Path, _title: str) -> Path:
        output_path.write_text("<html></html>", encoding="utf-8")
        return output_path

    monkeypatch.setattr("quant_engine.runner.write_tearsheet", fake_tearsheet)

    result = runner.invoke(
        app,
        [
            "backtest",
            "--strategy",
            "sma_cross",
            "--symbol",
            "SPY",
            "--from",
            "2024-01-02",
            "--to",
            "2024-01-03",
            "--tf",
            "5Min",
            "--cache-dir",
            str(tmp_path / "data"),
            "--results-dir",
            str(tmp_path / "results"),
            "--param",
            "fast=3",
            "--param",
            "slow=8",
            "--param",
            "atr_period=3",
        ],
    )

    assert result.exit_code == 0
    assert "Wrote results" in result.output


def test_cli_optimize_and_walkforward_use_cached_data(tmp_path: Path) -> None:
    frame = _daily_frame()
    request = DataRequest(
        symbol="SPY",
        start=date(2024, 1, 1),
        end=date(2024, 3, 31),
        timeframe="1d",
        provider="alpaca",
        cache_dir=tmp_path / "data",
    )
    save_cache(request, frame)

    optimize = runner.invoke(
        app,
        [
            "optimize",
            "--params",
            "fast=2..3,slow=5..6",
            "--strategy",
            "sma_cross",
            "--symbol",
            "SPY",
            "--from",
            "2024-01-01",
            "--to",
            "2024-03-31",
            "--tf",
            "1d",
            "--cache-dir",
            str(tmp_path / "data"),
            "--results-dir",
            str(tmp_path / "results"),
        ],
    )

    walkforward = runner.invoke(
        app,
        [
            "walkforward",
            "--params",
            "fast=2..3,slow=5..6",
            "--strategy",
            "sma_cross",
            "--symbol",
            "SPY",
            "--from",
            "2024-01-01",
            "--to",
            "2024-03-31",
            "--tf",
            "1d",
            "--train",
            "30d",
            "--test",
            "15d",
            "--cache-dir",
            str(tmp_path / "data"),
            "--results-dir",
            str(tmp_path / "results"),
        ],
    )

    assert optimize.exit_code == 0
    assert "Top parameter sets" in optimize.output
    assert walkforward.exit_code == 0
    assert "Walk-forward results" in walkforward.output


def _daily_frame() -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=91, freq="D", tz="UTC")
    trend = np.linspace(100, 130, len(index))
    wave = np.sin(np.linspace(0, 12, len(index))) * 3
    close = trend + wave
    return pd.DataFrame(
        {
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": np.full(len(index), 1_000_000),
            "openinterest": 0,
        },
        index=index,
    )
