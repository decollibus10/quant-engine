from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ProviderName = Literal["alpaca", "yfinance", "stooq"]


class Settings(BaseSettings):
    """Environment-backed credentials and defaults."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    alpaca_api_key_id: str | None = Field(default=None, alias="APCA_API_KEY_ID")
    alpaca_api_secret_key: str | None = Field(default=None, alias="APCA_API_SECRET_KEY")
    alpaca_feed: str = "iex"


class DataRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    symbol: str
    start: date
    end: date = Field(default_factory=date.today)
    timeframe: str = "5Min"
    provider: ProviderName = "alpaca"
    feed: str = "iex"
    adjustment: str = "raw"
    cache_dir: Path = Path("data")
    use_cache: bool = True

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        symbol = value.strip().upper()
        if not symbol:
            raise ValueError("symbol cannot be empty")
        return symbol

    @field_validator("timeframe", "feed", "adjustment")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("value cannot be empty")
        return text

    @model_validator(mode="after")
    def validate_range(self) -> DataRequest:
        if self.end < self.start:
            raise ValueError("end must be on or after start")
        return self


class BacktestRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: DataRequest
    strategy: str = "sma_cross"
    strategy_params: dict[str, Any] = Field(default_factory=dict)
    cash: float = 10_000.0
    commission: float = 0.0
    slippage_bps: float = 1.0
    results_dir: Path = Path("results")
    run_id: str | None = None

    @field_validator("strategy")
    @classmethod
    def normalize_strategy(cls, value: str) -> str:
        strategy = value.strip().lower()
        if not strategy:
            raise ValueError("strategy cannot be empty")
        return strategy

    @model_validator(mode="after")
    def validate_money(self) -> BacktestRequest:
        if self.cash <= 0:
            raise ValueError("cash must be positive")
        if self.commission < 0:
            raise ValueError("commission cannot be negative")
        if self.slippage_bps < 0:
            raise ValueError("slippage_bps cannot be negative")
        return self


class OptimizationRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    backtest: BacktestRequest
    params: dict[str, list[int | float | str]]
    metric: str = "sharpe"
    top_n: int = 10
    results_dir: Path = Path("results")

    @model_validator(mode="after")
    def validate_params(self) -> OptimizationRequest:
        if not self.params:
            raise ValueError("params cannot be empty")
        if self.top_n <= 0:
            raise ValueError("top_n must be positive")
        return self


class WalkForwardRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    backtest: BacktestRequest
    params: dict[str, list[int | float | str]]
    train_window: timedelta
    test_window: timedelta
    metric: str = "sharpe"
    top_n: int = 5
    results_dir: Path = Path("results")

    @model_validator(mode="after")
    def validate_windows(self) -> WalkForwardRequest:
        if self.train_window <= timedelta(0):
            raise ValueError("train_window must be positive")
        if self.test_window <= timedelta(0):
            raise ValueError("test_window must be positive")
        if not self.params:
            raise ValueError("params cannot be empty")
        return self
