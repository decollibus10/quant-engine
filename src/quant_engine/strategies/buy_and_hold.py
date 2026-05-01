from __future__ import annotations

import math
from typing import Any

import backtrader as bt


class BuyAndHold(bt.Strategy):
    params = (("cash_fraction_cap", 0.99),)

    def __init__(self) -> None:
        self.has_bought = False
        self.trade_log: list[dict[str, Any]] = []

    def next(self) -> None:
        if self.has_bought:
            return
        price = float(self.data.close[0])
        cash = float(self.broker.getcash())
        size = math.floor((cash * float(self.p.cash_fraction_cap)) / price)
        if size > 0:
            self.buy(size=size)
            self.has_bought = True

    def notify_trade(self, trade: bt.Trade) -> None:
        if not trade.isclosed:
            return
        self.trade_log.append(
            {
                "ref": trade.ref,
                "symbol": self.data._name,
                "size": float(trade.size),
                "entry_datetime": bt.num2date(trade.dtopen).isoformat(),
                "exit_datetime": bt.num2date(trade.dtclose).isoformat(),
                "entry_price": float(trade.price),
                "exit_price": float(self.data.close[0]),
                "barlen": int(trade.barlen),
                "pnl": float(trade.pnl),
                "pnl_comm": float(trade.pnlcomm),
            }
        )
