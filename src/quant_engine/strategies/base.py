from __future__ import annotations

import math
from typing import Any

import backtrader as bt

from quant_engine.risk.sizer import percent_risk_size
from quant_engine.risk.stops import atr_stop, fixed_percent_stop

BASE_PARAMS: tuple[tuple[str, object], ...] = (
    ("risk_pct", 0.01),
    ("atr_period", 14),
    ("atr_stop_mult", 2.0),
    ("fixed_stop_pct", 0.05),
    ("use_atr_stop", True),
    ("cash_fraction_cap", 0.95),
)


class BaseStrategy(bt.Strategy):
    params = BASE_PARAMS

    def __init__(self) -> None:
        self.atr = bt.ind.ATR(self.data, period=self.p.atr_period)
        self.order: bt.Order | None = None
        self.stop_order: bt.Order | None = None
        self.pending_stop_price: float | None = None
        self.trade_log: list[dict[str, Any]] = []
        self.order_log: list[dict[str, Any]] = []

    def should_enter(self) -> bool:
        return False

    def should_exit(self) -> bool:
        return False

    def next(self) -> None:
        if self.order:
            return
        if not self.position:
            if self.should_enter():
                self.enter_long()
            return
        if self.should_exit():
            self.exit_position()

    def enter_long(self) -> None:
        entry = float(self.data.close[0])
        stop = self.stop_price(entry)
        size = percent_risk_size(
            equity=float(self.broker.getvalue()),
            cash=float(self.broker.getcash()),
            entry_price=entry,
            stop_price=stop,
            risk_pct=float(self.p.risk_pct),
            cash_fraction_cap=float(self.p.cash_fraction_cap),
        )
        if size <= 0:
            return
        self.pending_stop_price = stop
        self.order = self.buy(size=size)

    def exit_position(self) -> None:
        if self.stop_order:
            self.cancel(self.stop_order)
            self.stop_order = None
        self.order = self.close()

    def stop_price(self, entry: float) -> float:
        if bool(self.p.use_atr_stop):
            atr_value = float(self.atr[0])
            if math.isfinite(atr_value) and atr_value > 0:
                return atr_stop(entry, atr_value, float(self.p.atr_stop_mult))
        return fixed_percent_stop(entry, float(self.p.fixed_stop_pct))

    def notify_order(self, order: bt.Order) -> None:
        status_name = order.getstatusname()
        if order.status in [order.Submitted, order.Accepted]:
            return

        self.order_log.append(
            {
                "datetime": self.data.datetime.datetime(0).isoformat(),
                "status": status_name,
                "side": "buy" if order.isbuy() else "sell",
                "size": float(order.executed.size),
                "price": float(order.executed.price),
                "value": float(order.executed.value),
                "commission": float(order.executed.comm),
            }
        )

        if order.status == order.Completed and order.isbuy() and self.pending_stop_price:
            self.stop_order = self.sell(
                exectype=bt.Order.Stop,
                price=self.pending_stop_price,
                size=order.executed.size,
            )
            self.pending_stop_price = None

        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            if order is self.order:
                self.order = None
            stop_order = self.stop_order
            if stop_order is not None and order is stop_order and order.status == order.Completed:
                self.stop_order = None

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
