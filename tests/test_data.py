from __future__ import annotations

from datetime import date

import pandas as pd

from quant_engine.config import DataRequest
from quant_engine.data.cache import cache_path, get_ohlcv, save_cache
from quant_engine.data.feed import OHLCVPandasData, to_backtrader_feed
from quant_engine.data.fetch import normalize_ohlcv


def test_cache_round_trip(sample_ohlcv: pd.DataFrame, tmp_path) -> None:
    request = DataRequest(
        symbol="SPY",
        start=date(2024, 1, 2),
        end=date(2024, 1, 3),
        cache_dir=tmp_path,
    )

    path = save_cache(request, sample_ohlcv)
    loaded = get_ohlcv(request)

    assert path == cache_path(request)
    assert len(loaded) == len(sample_ohlcv)
    assert list(loaded.columns) == list(sample_ohlcv.columns)


def test_normalize_ohlcv_lowercases_and_adds_openinterest() -> None:
    raw = pd.DataFrame(
        {
            "Open": [1.0],
            "High": [2.0],
            "Low": [0.5],
            "Close": [1.5],
            "Volume": [100],
        },
        index=pd.DatetimeIndex(["2024-01-02"]),
    )

    normalized = normalize_ohlcv(raw)

    assert list(normalized.columns) == ["open", "high", "low", "close", "volume", "openinterest"]
    assert normalized.index.tz is not None


def test_to_backtrader_feed_returns_feed(sample_ohlcv: pd.DataFrame) -> None:
    feed = to_backtrader_feed(sample_ohlcv, name="SPY")

    assert isinstance(feed, OHLCVPandasData)
