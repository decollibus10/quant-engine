from __future__ import annotations

import backtrader as bt

from quant_engine.strategies.base import BASE_PARAMS, BaseStrategy


class DonchianBreakout(BaseStrategy):
    params = BASE_PARAMS + (("lookback", 55),)

    def __init__(self) -> None:
        super().__init__()
        period = int(self.p.lookback)
        self.prior_high = bt.ind.Highest(self.data.high(-1), period=period)
        self.prior_low = bt.ind.Lowest(self.data.low(-1), period=period)

    def should_enter(self) -> bool:
        return bool(self.data.close[0] > self.prior_high[0])

    def should_exit(self) -> bool:
        return bool(self.data.close[0] < self.prior_low[0])
