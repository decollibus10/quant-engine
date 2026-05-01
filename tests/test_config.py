from __future__ import annotations

from datetime import date

import pytest

from quant_engine.config import DataRequest


def test_data_request_normalizes_symbol() -> None:
    request = DataRequest(symbol=" spy ", start=date(2024, 1, 1), end=date(2024, 1, 2))

    assert request.symbol == "SPY"


def test_data_request_rejects_inverted_dates() -> None:
    with pytest.raises(ValueError, match="end must be"):
        DataRequest(symbol="SPY", start=date(2024, 1, 2), end=date(2024, 1, 1))
