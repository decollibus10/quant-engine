from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from quant_engine.config import DataRequest

if TYPE_CHECKING:
    Fetcher = Callable[[DataRequest], pd.DataFrame]


def cache_key(request: DataRequest) -> str:
    payload = {
        "adjustment": request.adjustment.lower(),
        "end": request.end.isoformat(),
        "feed": request.feed.lower(),
        "provider": request.provider,
        "start": request.start.isoformat(),
        "symbol": request.symbol,
        "timeframe": request.timeframe,
    }
    serialized = json.dumps(payload, sort_keys=True)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:12]
    safe_timeframe = request.timeframe.replace("/", "-")
    return (
        f"{request.symbol}_{request.provider}_{safe_timeframe}_"
        f"{request.start.isoformat()}_{request.end.isoformat()}_{request.feed.lower()}_{digest}"
    )


def cache_path(request: DataRequest) -> Path:
    return request.cache_dir / request.provider / f"{cache_key(request)}.parquet"


def load_cache(request: DataRequest) -> pd.DataFrame | None:
    path = cache_path(request)
    if not path.exists():
        return None
    return pd.read_parquet(path)


def save_cache(request: DataRequest, frame: pd.DataFrame) -> Path:
    path = cache_path(request)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path)
    return path


def get_ohlcv(
    request: DataRequest, fetcher: Fetcher | None = None, force: bool = False
) -> pd.DataFrame:
    if request.use_cache and not force:
        cached = load_cache(request)
        if cached is not None:
            return cached

    if fetcher is None:
        from quant_engine.data.fetch import fetch_ohlcv

        fetcher = fetch_ohlcv

    frame = fetcher(request)
    if request.use_cache:
        save_cache(request, frame)
    return frame
