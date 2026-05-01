from __future__ import annotations

import backtrader as bt
import pandas as pd


class OHLCVPandasData(bt.feeds.PandasData):
    params = (
        ("datetime", None),
        ("open", "open"),
        ("high", "high"),
        ("low", "low"),
        ("close", "close"),
        ("volume", "volume"),
        ("openinterest", "openinterest"),
    )


def to_backtrader_feed(frame: pd.DataFrame, name: str | None = None) -> OHLCVPandasData:
    data = frame.copy()
    if isinstance(data.index, pd.DatetimeIndex) and data.index.tz is not None:
        data.index = data.index.tz_convert("UTC").tz_localize(None)
    return OHLCVPandasData(dataname=data, name=name)
