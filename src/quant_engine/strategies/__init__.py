from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import backtrader as bt

from quant_engine.strategies.buy_and_hold import BuyAndHold
from quant_engine.strategies.donchian_breakout import DonchianBreakout
from quant_engine.strategies.rsi_meanrev import RSIMeanReversion
from quant_engine.strategies.sma_cross import SMACrossover


@dataclass(frozen=True)
class StrategySpec:
    name: str
    strategy_class: type[bt.Strategy]
    default_params: dict[str, Any]
    description: str


STRATEGIES: dict[str, StrategySpec] = {
    "sma_cross": StrategySpec(
        name="sma_cross",
        strategy_class=SMACrossover,
        default_params={"fast": 20, "slow": 50},
        description="Fast SMA crosses above/below slow SMA.",
    ),
    "rsi_meanrev": StrategySpec(
        name="rsi_meanrev",
        strategy_class=RSIMeanReversion,
        default_params={"period": 14, "oversold": 30, "exit_rsi": 55},
        description="Buy oversold RSI and exit on mean reversion.",
    ),
    "donchian_breakout": StrategySpec(
        name="donchian_breakout",
        strategy_class=DonchianBreakout,
        default_params={"lookback": 55},
        description="Buy breakouts above prior Donchian high and exit below low.",
    ),
    "buy_and_hold": StrategySpec(
        name="buy_and_hold",
        strategy_class=BuyAndHold,
        default_params={},
        description="Benchmark that buys once and holds.",
    ),
}


def get_strategy(name: str) -> StrategySpec:
    normalized = name.strip().lower()
    try:
        return STRATEGIES[normalized]
    except KeyError as exc:
        valid = ", ".join(sorted(STRATEGIES))
        raise ValueError(f"unknown strategy '{name}'. Valid strategies: {valid}") from exc


def merged_strategy_params(name: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = get_strategy(name)
    merged = dict(spec.default_params)
    if params:
        merged.update(params)
    return merged
