from __future__ import annotations

import backtrader as bt

from quant_engine.strategies.base import BASE_PARAMS, BaseStrategy


class RSIMeanReversion(BaseStrategy):
    params = BASE_PARAMS + (
        ("period", 14),
        ("oversold", 30),
        ("exit_rsi", 55),
    )

    def __init__(self) -> None:
        super().__init__()
        self.rsi = bt.ind.RSI(self.data.close, period=int(self.p.period))

    def should_enter(self) -> bool:
        return bool(self.rsi[0] < float(self.p.oversold))

    def should_exit(self) -> bool:
        return bool(self.rsi[0] > float(self.p.exit_rsi))
