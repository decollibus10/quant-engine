from __future__ import annotations

from datetime import time
from typing import Any, cast

import pandas as pd

from quant_engine.config import DataRequest, Settings

STANDARD_COLUMNS = ["open", "high", "low", "close", "volume", "openinterest"]


def fetch_ohlcv(request: DataRequest) -> pd.DataFrame:
    if request.provider == "alpaca":
        return fetch_alpaca(request)
    if request.provider == "yfinance":
        return fetch_yfinance(request)
    if request.provider == "stooq":
        return fetch_stooq(request)
    raise ValueError(f"unsupported provider: {request.provider}")


def fetch_alpaca(request: DataRequest) -> pd.DataFrame:
    try:
        from alpaca.data.enums import Adjustment, DataFeed
        from alpaca.data.historical.stock import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
    except ImportError as exc:  # pragma: no cover - exercised when optional import is absent
        raise RuntimeError("alpaca-py is required for provider='alpaca'") from exc

    settings = Settings()
    if not settings.alpaca_api_key_id or not settings.alpaca_api_secret_key:
        raise RuntimeError("APCA_API_KEY_ID and APCA_API_SECRET_KEY are required for Alpaca data")

    client = StockHistoricalDataClient(settings.alpaca_api_key_id, settings.alpaca_api_secret_key)
    bar_request = StockBarsRequest(
        symbol_or_symbols=request.symbol,
        timeframe=_alpaca_timeframe(request.timeframe),
        start=_market_datetime(request.start, time.min),
        end=_market_datetime(request.end, time.max),
        feed=_enum_value(DataFeed, request.feed.upper()),
        adjustment=_enum_value(Adjustment, request.adjustment.upper()),
    )
    bars = cast(Any, client.get_stock_bars(bar_request))
    frame = bars.df
    if frame.empty:
        raise ValueError(f"no Alpaca bars returned for {request.symbol}")
    if isinstance(frame.index, pd.MultiIndex):
        frame = frame.xs(request.symbol, level=0)
    return normalize_ohlcv(frame, symbol=request.symbol)


def fetch_yfinance(request: DataRequest) -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise RuntimeError("yfinance is required for provider='yfinance'") from exc

    frame = yf.download(
        request.symbol,
        start=request.start.isoformat(),
        end=request.end.isoformat(),
        interval=_yfinance_interval(request.timeframe),
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    if frame.empty:
        raise ValueError(f"no yfinance bars returned for {request.symbol}")
    return normalize_ohlcv(frame, symbol=request.symbol)


def fetch_stooq(request: DataRequest) -> pd.DataFrame:
    try:
        from pandas_datareader import data as web
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise RuntimeError("pandas-datareader is required for provider='stooq'") from exc

    frame = web.DataReader(request.symbol, "stooq", request.start, request.end)
    if frame.empty:
        raise ValueError(f"no Stooq bars returned for {request.symbol}")
    return normalize_ohlcv(frame.sort_index(), symbol=request.symbol)


def normalize_ohlcv(frame: pd.DataFrame, symbol: str | None = None) -> pd.DataFrame:
    if frame.empty:
        raise ValueError("cannot normalize an empty OHLCV frame")

    data = _flatten_columns(frame.copy(), symbol=symbol)
    data.columns = [str(column).strip().lower().replace(" ", "_") for column in data.columns]
    data = data.rename(columns={"adj_close": "adjclose"})

    missing = {"open", "high", "low", "close", "volume"} - set(data.columns)
    if missing:
        raise ValueError(f"missing OHLCV columns: {sorted(missing)}")

    if "openinterest" not in data.columns:
        data["openinterest"] = 0

    data = data[STANDARD_COLUMNS].copy()
    for column in STANDARD_COLUMNS:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data.dropna(subset=["open", "high", "low", "close"]).sort_index()
    data.index = _timezone_aware_index(data.index)
    data.index.name = "datetime"
    return data


def _flatten_columns(frame: pd.DataFrame, symbol: str | None = None) -> pd.DataFrame:
    if not isinstance(frame.columns, pd.MultiIndex):
        return frame

    if symbol and symbol in frame.columns.get_level_values(-1):
        return frame.xs(symbol, axis=1, level=-1)
    if symbol and symbol in frame.columns.get_level_values(0):
        return frame.xs(symbol, axis=1, level=0)

    flattened = frame.copy()
    flattened.columns = [
        "_".join(str(part) for part in column if str(part) and str(part) != "nan")
        for column in flattened.columns
    ]
    return flattened


def _timezone_aware_index(index: pd.Index) -> pd.DatetimeIndex:
    dt_index = pd.DatetimeIndex(pd.to_datetime(index))
    if dt_index.tz is None:
        return dt_index.tz_localize("UTC")
    return dt_index


def _market_datetime(day: Any, session_time: time) -> pd.Timestamp:
    timestamp = pd.Timestamp.combine(pd.Timestamp(day).date(), session_time)
    return timestamp.tz_localize("America/New_York").tz_convert("UTC").to_pydatetime()


def _alpaca_timeframe(timeframe: str) -> Any:
    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

    amount, unit = _split_timeframe(timeframe)
    if unit == "minute":
        return TimeFrame(amount, TimeFrameUnit.Minute)
    if unit == "hour":
        return TimeFrame(amount, TimeFrameUnit.Hour)
    if unit == "day":
        if amount != 1:
            raise ValueError("Alpaca daily timeframe only supports 1 day bars")
        return TimeFrame.Day
    if unit == "week":
        if amount != 1:
            raise ValueError("Alpaca weekly timeframe only supports 1 week bars")
        return TimeFrame.Week
    if unit == "month":
        if amount != 1:
            raise ValueError("Alpaca monthly timeframe only supports 1 month bars")
        return TimeFrame.Month
    raise ValueError(f"unsupported Alpaca timeframe: {timeframe}")


def _yfinance_interval(timeframe: str) -> str:
    amount, unit = _split_timeframe(timeframe)
    suffix = {"minute": "m", "hour": "h", "day": "d", "week": "wk", "month": "mo"}[unit]
    return f"{amount}{suffix}"


def _split_timeframe(timeframe: str) -> tuple[int, str]:
    text = timeframe.strip().lower()
    unit_aliases = {
        "min": "minute",
        "m": "minute",
        "minute": "minute",
        "minutes": "minute",
        "h": "hour",
        "hour": "hour",
        "hours": "hour",
        "d": "day",
        "day": "day",
        "days": "day",
        "w": "week",
        "wk": "week",
        "week": "week",
        "weeks": "week",
        "mo": "month",
        "month": "month",
        "months": "month",
    }
    digits = "".join(character for character in text if character.isdigit())
    letters = "".join(character for character in text if character.isalpha())
    amount = int(digits) if digits else 1
    if letters not in unit_aliases:
        raise ValueError(f"unsupported timeframe: {timeframe}")
    return amount, unit_aliases[letters]


def _enum_value(enum_cls: Any, name: str) -> Any:
    try:
        return getattr(enum_cls, name)
    except AttributeError as exc:
        valid = [member.name.lower() for member in enum_cls]
        raise ValueError(
            f"unsupported {enum_cls.__name__}: {name.lower()} (valid: {valid})"
        ) from exc
