from __future__ import annotations


def fixed_percent_stop(entry_price: float, stop_pct: float) -> float:
    if entry_price <= 0:
        raise ValueError("entry_price must be positive")
    if not 0 < stop_pct < 1:
        raise ValueError("stop_pct must be between 0 and 1")
    return entry_price * (1 - stop_pct)


def atr_stop(entry_price: float, atr_value: float, multiplier: float) -> float:
    if entry_price <= 0:
        raise ValueError("entry_price must be positive")
    if atr_value <= 0:
        raise ValueError("atr_value must be positive")
    if multiplier <= 0:
        raise ValueError("multiplier must be positive")
    return entry_price - (atr_value * multiplier)
