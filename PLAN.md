# quant-engine Phase 0-5 Plan

## Summary

- Use `/Users/moof/Documents/Claude/Projects/Technical Analysis bot` as the repo root and create public GitHub repo `decollibus10/quant-engine`.
- Build the research engine through Phase 5: scaffold, Alpaca-first data, backtests, core strategies, optimization, and walk-forward.
- Default path: SPY, `5Min`, Alpaca free IEX feed, offline fixture tests in CI.
- Scope strategies to #1-3: SMA Crossover, RSI Mean Reversion, Donchian Breakout. No live trading.

## Key Changes

- Scaffold Python 3.11 project with `uv`, `src/quant_engine`, MIT license, README, `.gitignore`, CI, `data/` and `results/` ignored.
- Dependencies: `backtrader==1.9.78.123`, `alpaca-py`, `yfinance`, `pandas-datareader`, `pandas`, `numpy`, `pyarrow`, `pydantic`, `pydantic-settings`, `pyyaml`, `loguru`, `rich`, `typer`, `matplotlib`, `quantstats`, plus dev tools.
- Data layer supports `alpaca`, `yfinance`, and `stooq`; Alpaca uses env vars `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`, default feed `iex`, and cache keys by provider/symbol/timeframe/date/feed.
- CLI commands:
  - `quant fetch SPY --from 2024-01-01 --to 2024-12-31 --tf 5Min --provider alpaca`
  - `quant backtest --strategy sma_cross --symbol SPY --from 2024-01-01 --cash 10000`
  - `quant optimize --strategy sma_cross --symbol SPY --params fast=5..50,slow=20..200`
  - `quant walkforward --strategy sma_cross --symbol SPY --train 180d --test 30d`
- Runner emits `stats.json`, `equity_curve.csv`, equity-vs-benchmark PNG, trade log CSV, and quantstats HTML using daily-resampled returns for tear sheets.

## Implementation Details

- Create typed config models for data requests, backtest requests, strategy params, optimization params, and output paths.
- Normalize all OHLCV into a standard DataFrame: timezone-aware index plus `open/high/low/close/volume/openinterest`.
- Build a strategy registry so CLI names map to Backtrader classes and validated params.
- Add `BaseStrategy` with order/trade logging, stop handling, sizing hooks, and shared analyzer wiring.
- Add ATR/fixed-percent stop helpers and percent-risk/fixed-fractional sizers; benchmark buy-and-hold is the only no-stop exception.
- Implement grid optimization around repeated Backtrader runs, ranked by Sharpe by default, with top-N CSV/table and heatmap where two params are swept.
- Implement walk-forward windows: optimize on train, run best params on test, output in-sample vs out-of-sample summary.

## Test Plan

- CI runs `ruff check`, `black --check`, `mypy`, and `pytest`.
- Unit tests use offline fixtures only: cache round-trip, provider normalization, config validation, feed conversion, strategy registry, trade-log generation, optimization param parsing, and walk-forward splits.
- Live data tests are marked integration and skipped unless Alpaca credentials are present.
- Add smoke CLI tests with fixture data for `fetch`, `backtest`, `optimize`, and `walkforward`.

## Assumptions

- Current folder becomes the repo root; no nested `quant-engine/` folder.
- Public GitHub creation is part of implementation.
- `PLAN.md` reflects these locked choices.
- Alpaca API shape follows official `StockHistoricalDataClient.get_stock_bars` and `StockBarsRequest` docs.
