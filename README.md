# quant-engine

Intraday-first stock strategy research engine powered by Backtrader.

The day-one goal is fast research: fetch historical candles, run a strategy, inspect stats, equity curve, trade log, and reports. Live trading is intentionally out of scope.

## Quickstart

```bash
uv sync --extra dev
```

For Alpaca historical bars, set:

```bash
export APCA_API_KEY_ID="..."
export APCA_API_SECRET_KEY="..."
```

Fetch SPY 5-minute bars from Alpaca's free IEX feed:

```bash
uv run quant fetch SPY --from 2024-01-01 --to 2024-12-31 --tf 5Min --provider alpaca
```

Run a backtest:

```bash
uv run quant backtest --strategy sma_cross --symbol SPY --from 2024-01-01 --cash 10000
```

Optimize SMA parameters:

```bash
uv run quant optimize --strategy sma_cross --symbol SPY --from 2024-01-01 --params fast=5..50,slow=20..200
```

Walk-forward test:

```bash
uv run quant walkforward --strategy sma_cross --symbol SPY --from 2022-01-01 --to 2024-12-31 --train 180d --test 30d --params fast=5..30:5,slow=40..120:20
```

## Outputs

Backtests write one run folder under `results/` with:

- `stats.json`
- `equity_curve.csv`
- `trade_log.csv`
- `equity_curve.png`
- `tearsheet.html`

Optimization and walk-forward commands write CSV/JSON summaries and plots under `results/` as well.

## Strategies

Implemented core research strategies:

- `sma_cross`
- `rsi_meanrev`
- `donchian_breakout`
- `buy_and_hold` benchmark

All active strategies use risk-based sizing and a stop-loss. The benchmark is the only stop-free strategy.

## Data Sources

- `alpaca`: default for intraday. Uses `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`, feed `iex`.
- `yfinance`: free Yahoo fallback.
- `stooq`: free daily fallback through pandas-datareader.

Downloaded data is cached as parquet under `data/` using provider, symbol, timeframe, range, feed, and adjustment.

## Quality

```bash
uv run ruff check .
uv run black --check .
uv run mypy src tests
uv run pytest
```

CI runs the same checks. Tests are offline by default; live data checks are marked `integration` and skipped unless credentials are present.
