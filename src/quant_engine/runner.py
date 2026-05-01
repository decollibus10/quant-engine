from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import backtrader as bt
import matplotlib
import pandas as pd

matplotlib.use("Agg")
from matplotlib import pyplot as plt

from quant_engine.analyzers.equity import EquityCurve
from quant_engine.analyzers.tearsheet import daily_returns, write_tearsheet
from quant_engine.analyzers.trades import trades_to_frame, write_trade_log
from quant_engine.config import BacktestRequest
from quant_engine.data.cache import get_ohlcv
from quant_engine.data.feed import to_backtrader_feed
from quant_engine.strategies import get_strategy, merged_strategy_params


@dataclass(frozen=True)
class BacktestResult:
    stats: dict[str, Any]
    equity_curve: pd.DataFrame
    trade_log: pd.DataFrame
    output_dir: Path | None


def run_backtest(
    request: BacktestRequest,
    data: pd.DataFrame | None = None,
    *,
    write_outputs: bool = True,
    include_benchmark: bool = True,
) -> BacktestResult:
    frame = data if data is not None else get_ohlcv(request.data)
    strategy_result = _run_single(request, frame)

    benchmark_equity: pd.DataFrame | None = None
    benchmark_stats: dict[str, Any] | None = None
    if include_benchmark and request.strategy != "buy_and_hold":
        benchmark_request = request.model_copy(
            update={"strategy": "buy_and_hold", "strategy_params": {}, "run_id": None}
        )
        benchmark = _run_single(benchmark_request, frame)
        benchmark_equity = benchmark.equity_curve
        benchmark_stats = benchmark.stats
        strategy_result.stats["benchmark"] = {
            "final_value": benchmark_stats["final_value"],
            "total_return_pct": benchmark_stats["total_return_pct"],
            "max_drawdown_pct": benchmark_stats["max_drawdown_pct"],
            "sharpe": benchmark_stats["sharpe"],
        }

    output_dir: Path | None = None
    if write_outputs:
        output_dir = _output_dir(request)
        output_dir.mkdir(parents=True, exist_ok=True)
        strategy_result.equity_curve.to_csv(output_dir / "equity_curve.csv")
        write_trade_log(strategy_result.trade_log.to_dict("records"), output_dir / "trade_log.csv")
        _write_json(output_dir / "stats.json", strategy_result.stats)
        _plot_equity(
            strategy_result.equity_curve,
            output_dir / "equity_curve.png",
            benchmark_equity=benchmark_equity,
            title=f"{request.strategy} {request.data.symbol}",
        )
        write_tearsheet(
            strategy_result.equity_curve,
            output_dir / "tearsheet.html",
            f"{request.strategy} {request.data.symbol}",
        )

    return BacktestResult(
        stats=strategy_result.stats,
        equity_curve=strategy_result.equity_curve,
        trade_log=strategy_result.trade_log,
        output_dir=output_dir,
    )


def _run_single(request: BacktestRequest, data: pd.DataFrame) -> BacktestResult:
    spec = get_strategy(request.strategy)
    params = merged_strategy_params(request.strategy, request.strategy_params)

    cerebro = bt.Cerebro(stdstats=False)
    cerebro.broker.setcash(request.cash)
    cerebro.broker.setcommission(commission=request.commission)
    cerebro.broker.set_slippage_perc(perc=request.slippage_bps / 10_000)
    cerebro.adddata(to_backtrader_feed(data, name=request.data.symbol))
    cerebro.addstrategy(spec.strategy_class, **params)
    cerebro.addanalyzer(EquityCurve, _name="equity")

    run = cerebro.run(maxcpus=1)
    strategy = run[0]
    equity_curve = pd.DataFrame(strategy.analyzers.equity.get_analysis())
    if equity_curve.empty:
        equity_curve = pd.DataFrame(columns=["value", "cash"])
        equity_curve.index.name = "datetime"
    else:
        equity_curve["datetime"] = pd.to_datetime(equity_curve["datetime"])
        equity_curve = equity_curve.set_index("datetime").sort_index()

    trade_log = trades_to_frame(getattr(strategy, "trade_log", []))
    stats = _stats(request, equity_curve, trade_log)
    return BacktestResult(
        stats=stats, equity_curve=equity_curve, trade_log=trade_log, output_dir=None
    )


def _stats(
    request: BacktestRequest, equity_curve: pd.DataFrame, trade_log: pd.DataFrame
) -> dict[str, Any]:
    if equity_curve.empty:
        final_value = request.cash
        max_drawdown = 0.0
        sharpe = 0.0
        annual_return = 0.0
    else:
        values = equity_curve["value"]
        final_value = float(values.iloc[-1])
        drawdown = (values / values.cummax()) - 1
        max_drawdown = float(drawdown.min() * 100)
        returns = daily_returns(equity_curve)
        sharpe = _sharpe(returns)
        annual_return = _annualized_return(values)

    total_return_pct = ((final_value / request.cash) - 1) * 100
    closed_trades = len(trade_log)
    wins = int((trade_log["pnl_comm"] > 0).sum()) if closed_trades else 0
    win_rate = (wins / closed_trades * 100) if closed_trades else 0.0

    return {
        "strategy": request.strategy,
        "symbol": request.data.symbol,
        "provider": request.data.provider,
        "timeframe": request.data.timeframe,
        "start": request.data.start.isoformat(),
        "end": request.data.end.isoformat(),
        "cash": request.cash,
        "final_value": final_value,
        "total_return_pct": total_return_pct,
        "annual_return_pct": annual_return,
        "max_drawdown_pct": max_drawdown,
        "sharpe": sharpe,
        "closed_trades": closed_trades,
        "win_rate_pct": win_rate,
        "params": merged_strategy_params(request.strategy, request.strategy_params),
    }


def _sharpe(returns: pd.Series) -> float:
    if returns.empty or returns.std(ddof=0) == 0:
        return 0.0
    return float((returns.mean() / returns.std(ddof=0)) * (252**0.5))


def _annualized_return(values: pd.Series) -> float:
    if len(values) < 2:
        return 0.0
    first = float(values.iloc[0])
    last = float(values.iloc[-1])
    if first <= 0:
        return 0.0
    elapsed_days = max((values.index[-1] - values.index[0]).days, 1)
    years = elapsed_days / 365.25
    return float(((last / first) ** (1 / years) - 1) * 100)


def _plot_equity(
    equity_curve: pd.DataFrame,
    output_path: Path,
    *,
    benchmark_equity: pd.DataFrame | None,
    title: str,
) -> None:
    fig, ax = plt.subplots(figsize=(12, 6))
    if not equity_curve.empty:
        ax.plot(equity_curve.index, equity_curve["value"], label="Strategy", linewidth=1.8)
    if benchmark_equity is not None and not benchmark_equity.empty:
        ax.plot(
            benchmark_equity.index, benchmark_equity["value"], label="Buy & hold", linewidth=1.4
        )
    ax.set_title(title)
    ax.set_xlabel("Date")
    ax.set_ylabel("Equity")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _output_dir(request: BacktestRequest) -> Path:
    run_id = request.run_id
    if run_id is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = f"{timestamp}_{request.strategy}_{request.data.symbol}_{request.data.timeframe}"
    return request.results_dir / run_id


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
