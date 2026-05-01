from __future__ import annotations

from datetime import date

import pandas as pd

from quant_engine.config import BacktestRequest, DataRequest
from quant_engine.runner import run_backtest
from quant_engine.strategies import get_strategy, merged_strategy_params


def test_strategy_registry_merges_defaults() -> None:
    assert get_strategy("sma_cross").name == "sma_cross"
    assert merged_strategy_params("sma_cross", {"fast": 5})["slow"] == 50


def test_run_backtest_smoke(sample_ohlcv: pd.DataFrame, tmp_path) -> None:
    request = BacktestRequest(
        data=DataRequest(
            symbol="SPY",
            start=date(2024, 1, 2),
            end=date(2024, 1, 3),
            cache_dir=tmp_path / "data",
        ),
        strategy="sma_cross",
        strategy_params={"fast": 3, "slow": 8, "atr_period": 3},
        results_dir=tmp_path / "results",
    )

    result = run_backtest(request, data=sample_ohlcv, write_outputs=True)

    assert result.stats["strategy"] == "sma_cross"
    assert result.stats["final_value"] > 0
    assert result.output_dir is not None
    assert (result.output_dir / "stats.json").exists()
    assert (result.output_dir / "equity_curve.csv").exists()
    assert (result.output_dir / "trade_log.csv").exists()
    assert (result.output_dir / "equity_curve.png").exists()
    assert (result.output_dir / "tearsheet.html").exists()
