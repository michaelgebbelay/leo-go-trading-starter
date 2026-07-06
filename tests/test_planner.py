from __future__ import annotations

import json
from pathlib import Path

from leo_go_trading.models import TradeSignal
from leo_go_trading.brokers.tastytrade_payload import tastytrade_order_preview
from leo_go_trading.cli import load_env_file
from leo_go_trading.planner import build_condor_plan, build_vertical_bundle_plan


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


def test_constantstable_risk_reversal_plan_uses_left_right_go() -> None:
    payload = json.loads(Path("examples/sample_constantstable_trade.json").read_text())
    signal = TradeSignal.from_payload(payload, endpoint="rapi/GetUltraPureConstantStable")
    plan = build_vertical_bundle_plan(signal, quantity=3)

    assert signal.schema == "ConstantStable-like"
    assert plan.structure == "RR_LONG_CALL"
    assert plan.order_type == "MIXED"
    assert [leg.action for leg in plan.legs] == [
        "SELL_TO_OPEN",
        "BUY_TO_OPEN",
        "BUY_TO_OPEN",
        "SELL_TO_OPEN",
    ]
    assert [leg.quantity for leg in plan.legs] == [3, 3, 3, 3]


def test_novix_full_long_ic_plan() -> None:
    payload = json.loads(Path("examples/sample_novix_trade.json").read_text())
    signal = TradeSignal.from_payload(payload, endpoint="rapi/GetNovix")
    plan = build_vertical_bundle_plan(signal, quantity=1)

    assert signal.schema == "Novix-like"
    assert plan.structure == "IC_LONG"
    assert plan.order_type == "NET_DEBIT"
    assert [leg.strike for leg in plan.legs] == [6200.0, 6195.0, 6280.0, 6285.0]


def test_tastytrade_preview_infers_debit_for_long_ic() -> None:
    payload = json.loads(Path("examples/sample_novix_trade.json").read_text())
    signal = TradeSignal.from_payload(payload, endpoint="rapi/GetNovix")
    plan = build_vertical_bundle_plan(signal, quantity=1)
    preview = tastytrade_order_preview(plan, limit_price=1.1)

    assert preview["price-effect"] == "Debit"
    assert preview["legs"][0]["action"] == "Buy to Open"
    assert preview["legs"][0]["symbol"] == "SPXW260706P06200000"
    assert "symbol-note" in preview["metadata"]


def test_leoprofit_planner_rejects_leftgo_signal() -> None:
    payload = json.loads(Path("examples/sample_constantstable_trade.json").read_text())
    signal = TradeSignal.from_payload(payload, endpoint="rapi/GetUltraPureConstantStable")

    try:
        build_condor_plan(signal)
    except ValueError as exc:
        assert "Cat1 and Cat2" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_load_env_file_does_not_override_existing_env(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("GW_BASE=https://example.invalid\nGW_TOKEN=from-file\n")
    monkeypatch.setenv("GW_TOKEN", "already-set")

    load_env_file(str(env_file))

    assert "example.invalid" in __import__("os").environ["GW_BASE"]
    assert __import__("os").environ["GW_TOKEN"] == "already-set"
