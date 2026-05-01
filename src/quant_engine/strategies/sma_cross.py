from __future__ import annotations

import backtrader as bt

from quant_engine.strategies.base import BASE_PARAMS, BaseStrategy


class SMACrossover(BaseStrategy):
    params = BASE_PARAMS + (
        ("fast", 20),
        ("slow", 50),
    )

    def __init__(self) -> None:
        super().__init__()
        if int(self.p.fast) >= int(self.p.slow):
            raise ValueError("fast SMA period must be less than slow SMA period")
        self.fast_sma = bt.ind.SMA(self.data.close, period=int(self.p.fast))
        self.slow_sma = bt.ind.SMA(self.data.close, period=int(self.p.slow))
        self.cross = bt.ind.CrossOver(self.fast_sma, self.slow_sma)

    def should_enter(self) -> bool:
        return bool(self.cross[0] > 0)

    def should_exit(self) -> bool:
        return bool(self.cross[0] < 0)
