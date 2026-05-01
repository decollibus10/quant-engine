from __future__ import annotations

from typing import Any

import backtrader as bt


class EquityCurve(bt.Analyzer):
    def start(self) -> None:
        self.values: list[dict[str, Any]] = []

    def next(self) -> None:
        self.values.append(
            {
                "datetime": self.strategy.datetime.datetime(0),
                "value": float(self.strategy.broker.getvalue()),
                "cash": float(self.strategy.broker.getcash()),
            }
        )

    def get_analysis(self) -> list[dict[str, Any]]:
        return self.values
