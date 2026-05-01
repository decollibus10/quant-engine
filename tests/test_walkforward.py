from __future__ import annotations

import pandas as pd

from quant_engine.optimize.walkforward import build_windows, parse_duration


def test_parse_duration() -> None:
    assert parse_duration("30d").days == 30
    assert parse_duration("2w").days == 14


def test_build_windows() -> None:
    index = pd.date_range("2024-01-01", periods=20, freq="D", tz="UTC")

    windows = build_windows(index, parse_duration("5d"), parse_duration("3d"))

    assert len(windows) >= 4
    assert windows[0]["train_start"] == index[0]
