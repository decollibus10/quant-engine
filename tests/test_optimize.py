from __future__ import annotations

from quant_engine.optimize.grid import parameter_combinations, parse_param_grid


def test_parse_param_grid_supports_ranges_and_steps() -> None:
    parsed = parse_param_grid("fast=5..15:5,slow=20..40:10,mode=a|b")

    assert parsed == {"fast": [5, 10, 15], "slow": [20, 30, 40], "mode": ["a", "b"]}


def test_parameter_combinations() -> None:
    combos = parameter_combinations({"fast": [5, 10], "slow": [20]})

    assert combos == [{"fast": 5, "slow": 20}, {"fast": 10, "slow": 20}]
