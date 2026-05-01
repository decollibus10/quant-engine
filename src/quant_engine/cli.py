from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from quant_engine.config import (
    BacktestRequest,
    DataRequest,
    OptimizationRequest,
    ProviderName,
    WalkForwardRequest,
)
from quant_engine.data.cache import cache_path, get_ohlcv
from quant_engine.optimize.grid import parse_param_grid, run_grid_optimization
from quant_engine.optimize.walkforward import parse_duration, run_walkforward
from quant_engine.runner import run_backtest
from quant_engine.strategies import STRATEGIES

app = typer.Typer(no_args_is_help=True, help="Stock strategy research engine.")
console = Console()


@app.command("fetch")
def fetch_command(
    symbol: Annotated[str, typer.Argument(help="Ticker symbol, e.g. SPY")],
    from_date: Annotated[str, typer.Option("--from", help="Start date, YYYY-MM-DD")],
    to_date: Annotated[str | None, typer.Option("--to", help="End date, YYYY-MM-DD")] = None,
    timeframe: Annotated[str, typer.Option("--tf", help="Timeframe, e.g. 5Min or 1d")] = "5Min",
    provider: Annotated[ProviderName, typer.Option(help="Data provider")] = "alpaca",
    feed: Annotated[str, typer.Option(help="Alpaca feed")] = "iex",
    cache_dir: Annotated[Path, typer.Option(help="Parquet cache directory")] = Path("data"),
    force: Annotated[bool, typer.Option(help="Re-download even when cached")] = False,
) -> None:
    request = DataRequest(
        symbol=symbol,
        start=_parse_date(from_date),
        end=_parse_date(to_date),
        timeframe=timeframe,
        provider=provider,
        feed=feed,
        cache_dir=cache_dir,
    )
    frame = get_ohlcv(request, force=force)
    table = Table(title=f"{request.symbol} {request.timeframe} bars")
    table.add_column("Rows", justify="right")
    table.add_column("Start")
    table.add_column("End")
    table.add_column("Cache")
    table.add_row(
        str(len(frame)),
        str(frame.index.min()),
        str(frame.index.max()),
        str(cache_path(request)),
    )
    console.print(table)


@app.command("backtest")
def backtest_command(
    strategy: Annotated[str, typer.Option("--strategy", help="Strategy name")] = "sma_cross",
    symbol: Annotated[str, typer.Option("--symbol", help="Ticker symbol")] = "SPY",
    from_date: Annotated[str, typer.Option("--from", help="Start date, YYYY-MM-DD")] = "2024-01-01",
    to_date: Annotated[str | None, typer.Option("--to", help="End date, YYYY-MM-DD")] = None,
    timeframe: Annotated[str, typer.Option("--tf", help="Timeframe")] = "5Min",
    provider: Annotated[ProviderName, typer.Option(help="Data provider")] = "alpaca",
    feed: Annotated[str, typer.Option(help="Alpaca feed")] = "iex",
    cash: Annotated[float, typer.Option(help="Starting cash")] = 10_000.0,
    param: Annotated[
        list[str] | None, typer.Option("--param", "-p", help="Strategy parameter key=value")
    ] = None,
    cache_dir: Annotated[Path, typer.Option(help="Parquet cache directory")] = Path("data"),
    results_dir: Annotated[Path, typer.Option(help="Results directory")] = Path("results"),
) -> None:
    request = _backtest_request(
        strategy=strategy,
        symbol=symbol,
        from_date=from_date,
        to_date=to_date,
        timeframe=timeframe,
        provider=provider,
        feed=feed,
        cash=cash,
        params=_parse_key_value_params(param or []),
        cache_dir=cache_dir,
        results_dir=results_dir,
    )
    result = run_backtest(request)
    _print_stats(result.stats)
    if result.output_dir:
        console.print(f"[green]Wrote results:[/green] {result.output_dir}")


@app.command("optimize")
def optimize_command(
    params: Annotated[
        str, typer.Option("--params", help="Grid expression, e.g. fast=5..50,slow=20..200")
    ],
    strategy: Annotated[str, typer.Option("--strategy", help="Strategy name")] = "sma_cross",
    symbol: Annotated[str, typer.Option("--symbol", help="Ticker symbol")] = "SPY",
    from_date: Annotated[str, typer.Option("--from", help="Start date, YYYY-MM-DD")] = "2024-01-01",
    to_date: Annotated[str | None, typer.Option("--to", help="End date, YYYY-MM-DD")] = None,
    timeframe: Annotated[str, typer.Option("--tf", help="Timeframe")] = "5Min",
    provider: Annotated[ProviderName, typer.Option(help="Data provider")] = "alpaca",
    feed: Annotated[str, typer.Option(help="Alpaca feed")] = "iex",
    cash: Annotated[float, typer.Option(help="Starting cash")] = 10_000.0,
    metric: Annotated[str, typer.Option(help="Ranking metric")] = "sharpe",
    top_n: Annotated[int, typer.Option(help="Number of rows to print/save")] = 10,
    cache_dir: Annotated[Path, typer.Option(help="Parquet cache directory")] = Path("data"),
    results_dir: Annotated[Path, typer.Option(help="Results directory")] = Path("results"),
) -> None:
    backtest = _backtest_request(
        strategy=strategy,
        symbol=symbol,
        from_date=from_date,
        to_date=to_date,
        timeframe=timeframe,
        provider=provider,
        feed=feed,
        cash=cash,
        params={},
        cache_dir=cache_dir,
        results_dir=results_dir,
    )
    request = OptimizationRequest(
        backtest=backtest,
        params=parse_param_grid(params),
        metric=metric,
        top_n=top_n,
        results_dir=results_dir,
    )
    results = run_grid_optimization(request)
    _print_dataframe(results.head(top_n), title="Top parameter sets")


@app.command("walkforward")
def walkforward_command(
    params: Annotated[str, typer.Option("--params", help="Grid expression")],
    strategy: Annotated[str, typer.Option("--strategy", help="Strategy name")] = "sma_cross",
    symbol: Annotated[str, typer.Option("--symbol", help="Ticker symbol")] = "SPY",
    from_date: Annotated[str, typer.Option("--from", help="Start date, YYYY-MM-DD")] = "2022-01-01",
    to_date: Annotated[str | None, typer.Option("--to", help="End date, YYYY-MM-DD")] = None,
    train: Annotated[str, typer.Option("--train", help="Train window, e.g. 180d")] = "180d",
    test: Annotated[str, typer.Option("--test", help="Test window, e.g. 30d")] = "30d",
    timeframe: Annotated[str, typer.Option("--tf", help="Timeframe")] = "5Min",
    provider: Annotated[ProviderName, typer.Option(help="Data provider")] = "alpaca",
    feed: Annotated[str, typer.Option(help="Alpaca feed")] = "iex",
    cash: Annotated[float, typer.Option(help="Starting cash")] = 10_000.0,
    metric: Annotated[str, typer.Option(help="Optimization metric")] = "sharpe",
    cache_dir: Annotated[Path, typer.Option(help="Parquet cache directory")] = Path("data"),
    results_dir: Annotated[Path, typer.Option(help="Results directory")] = Path("results"),
) -> None:
    backtest = _backtest_request(
        strategy=strategy,
        symbol=symbol,
        from_date=from_date,
        to_date=to_date,
        timeframe=timeframe,
        provider=provider,
        feed=feed,
        cash=cash,
        params={},
        cache_dir=cache_dir,
        results_dir=results_dir,
    )
    request = WalkForwardRequest(
        backtest=backtest,
        params=parse_param_grid(params),
        train_window=parse_duration(train),
        test_window=parse_duration(test),
        metric=metric,
        results_dir=results_dir,
    )
    results = run_walkforward(request)
    _print_dataframe(results, title="Walk-forward results")


@app.command("strategies")
def strategies_command() -> None:
    table = Table(title="Available strategies")
    table.add_column("Name")
    table.add_column("Defaults")
    table.add_column("Description")
    for spec in STRATEGIES.values():
        table.add_row(spec.name, str(spec.default_params), spec.description)
    console.print(table)


def _backtest_request(
    *,
    strategy: str,
    symbol: str,
    from_date: str | date,
    to_date: str | date | None,
    timeframe: str,
    provider: ProviderName,
    feed: str,
    cash: float,
    params: dict[str, Any],
    cache_dir: Path,
    results_dir: Path,
) -> BacktestRequest:
    data_request = DataRequest(
        symbol=symbol,
        start=_parse_date(from_date),
        end=_parse_date(to_date),
        timeframe=timeframe,
        provider=provider,
        feed=feed,
        cache_dir=cache_dir,
    )
    return BacktestRequest(
        data=data_request,
        strategy=strategy,
        strategy_params=params,
        cash=cash,
        results_dir=results_dir,
    )


def _parse_key_value_params(values: list[str]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for value in values:
        key, raw = value.split("=", maxsplit=1)
        parsed[key.strip()] = _coerce_value(raw.strip())
    return parsed


def _parse_date(value: str | date | None) -> date:
    if value is None:
        return date.today()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter("expected date in YYYY-MM-DD format") from exc


def _coerce_value(raw: str) -> Any:
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except ValueError:
        lowered = raw.lower()
        if lowered in {"true", "false"}:
            return lowered == "true"
        return raw


def _print_stats(stats: dict[str, Any]) -> None:
    table = Table(title="Backtest stats")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    for key in [
        "strategy",
        "symbol",
        "timeframe",
        "final_value",
        "total_return_pct",
        "annual_return_pct",
        "max_drawdown_pct",
        "sharpe",
        "closed_trades",
        "win_rate_pct",
    ]:
        table.add_row(
            key, str(round(stats[key], 4)) if isinstance(stats[key], float) else str(stats[key])
        )
    console.print(table)


def _print_dataframe(frame: Any, title: str) -> None:
    table = Table(title=title)
    for column in frame.columns:
        table.add_column(str(column))
    for _, row in frame.iterrows():
        table.add_row(
            *[str(round(value, 4)) if isinstance(value, float) else str(value) for value in row]
        )
    console.print(table)


if __name__ == "__main__":
    app()
