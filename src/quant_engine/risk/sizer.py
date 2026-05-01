from __future__ import annotations

import math


def fixed_fractional_size(cash: float, price: float, fraction: float = 0.95) -> int:
    if cash <= 0 or price <= 0 or fraction <= 0:
        return 0
    return max(0, math.floor((cash * fraction) / price))


def percent_risk_size(
    equity: float,
    cash: float,
    entry_price: float,
    stop_price: float,
    risk_pct: float,
    cash_fraction_cap: float = 0.95,
) -> int:
    per_share_risk = entry_price - stop_price
    if equity <= 0 or cash <= 0 or entry_price <= 0 or per_share_risk <= 0 or risk_pct <= 0:
        return 0
    risk_cash = equity * risk_pct
    risk_size = math.floor(risk_cash / per_share_risk)
    cash_size = fixed_fractional_size(cash, entry_price, cash_fraction_cap)
    return max(0, min(risk_size, cash_size))
