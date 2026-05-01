from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

TRADE_COLUMNS = [
    "ref",
    "symbol",
    "size",
    "entry_datetime",
    "exit_datetime",
    "entry_price",
    "exit_price",
    "barlen",
    "pnl",
    "pnl_comm",
]


def trades_to_frame(trades: list[dict[str, Any]]) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame(columns=TRADE_COLUMNS)
    return pd.DataFrame(trades).reindex(columns=TRADE_COLUMNS)


def write_trade_log(trades: list[dict[str, Any]], path: Path) -> pd.DataFrame:
    frame = trades_to_frame(trades)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return frame
