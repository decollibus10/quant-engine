from __future__ import annotations

from pathlib import Path

DEFAULT_SINGLE_SYMBOLS = ["SPY"]


def load_symbols_csv(path: Path) -> list[str]:
    symbols: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        symbol = line.strip().split(",", maxsplit=1)[0].upper()
        if symbol and symbol != "SYMBOL":
            symbols.append(symbol)
    return symbols
