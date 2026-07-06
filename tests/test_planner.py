from __future__ import annotations

import json
from pathlib import Path

from leo_go_trading.models import TradeSignal
from leo_go_trading.planner import build_condor_plan


def sample_signal() -> TradeSignal:
    payload = json.loads(Path("examples/sample_leoprofit_trade.json").read_text())
    return TradeSignal.from_payload(payload, endpoint="rapi/GetLeoProfit")


def test_credit_plan_uses_ratio_call_side() -> None:
    plan = build_condor_plan(sample_signal(), quantity=2, put_width=20, call_width=10, call_multiplier=2)

    assert plan.side == "CREDIT"
    assert plan.order_type == "NET_CREDIT"
    assert [leg.quantity for leg in plan.legs] == [2, 2, 4, 4]
    assert [leg.strike for leg in plan.legs] == [6180.0, 6200.0, 6280.0, 6290.0]


def test_debit_override_uses_five_wide_long_condor() -> None:
    plan = build_condor_plan(sample_signal(), quantity=1, side_override="DEBIT")

    assert plan.side == "DEBIT"
    assert plan.order_type == "NET_DEBIT"
    assert [leg.quantity for leg in plan.legs] == [1, 1, 1, 1]
    assert [leg.strike for leg in plan.legs] == [6200.0, 6195.0, 6285.0, 6280.0]


def test_nested_trade_payload_is_supported() -> None:
    payload = {"outer": {"Trade": [{"TDate": "2026-07-06", "Limit": "6200", "CLimit": "6280"}]}}
    signal = TradeSignal.from_payload(payload, endpoint="rapi/GetLeoCross")

    assert signal.side == "CREDIT"
    assert signal.short_put == 6200
    assert signal.short_call == 6280
