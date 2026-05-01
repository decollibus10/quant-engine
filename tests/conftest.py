from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def sample_ohlcv() -> pd.DataFrame:
    index = pd.date_range("2024-01-02 09:30", periods=240, freq="5min", tz="UTC")
    trend = np.linspace(100, 120, len(index))
    wave = np.sin(np.linspace(0, 20, len(index))) * 2
    close = trend + wave
    open_ = close - 0.2
    high = close + 0.6
    low = close - 0.7
    volume = np.full(len(index), 100_000)
    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "openinterest": 0,
        },
        index=index,
    )
