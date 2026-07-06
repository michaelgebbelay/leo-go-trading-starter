from __future__ import annotations

import json
from pathlib import Path

import pytest

from leo_go_trading.execution import ExecutionPolicy, build_execution_preview
from leo_go_trading.models import TradeSignal
from leo_go_trading.planner import build_condor_plan, build_vertical_bundle_plan


def _signal(path: str, endpoint: str) -> TradeSignal:
    payload = json.loads(Path(path).read_text())
    return TradeSignal.from_payload(payload, endpoint=endpoint)


def _priced_policy(mode: str = "verticals") -> ExecutionPolicy:
    return ExecutionPolicy(
        profile="test",
        execution_mode=mode,
        min_credit_per_vertical=0.20,
        min_credit_full_package=0.40,
        max_debit_per_vertical=1.10,
        max_debit_full_package=2.20,
        price_step=0.05,
        max_attempts=3,
        vertical_sequence=("put", "call"),
        stop_if_first_vertical_fails=True,
        require_manual_review_after_partial_fill=True,
        max_contracts_per_leg=10,
        reject_stale_signal_minutes=15,
    )


def test_leoprofit_credit_ic_splits_into_credit_verticals() -> None:
    signal = _signal("examples/sample_leoprofit_trade.json", "rapi/GetLeoProfit")
    plan = build_condor_plan(signal, quantity=1, call_multiplier=1)

    preview = build_execution_preview(plan, _priced_policy())

    assert preview["dry_run_only"] is True
    assert preview["execution_mode"] == "verticals"
    assert [step["vertical"] for step in preview["steps"]] == ["put", "call"]
    assert [step["side"] for step in preview["steps"]] == ["CREDIT", "CREDIT"]
    assert [step["min_credit"] for step in preview["steps"]] == [0.20, 0.20]


def test_leoprofit_debit_ic_splits_into_debit_verticals() -> None:
    signal = _signal("examples/sample_leoprofit_trade.json", "rapi/GetLeoProfit")
    plan = build_condor_plan(signal, quantity=1, side_override="DEBIT")

    preview = build_execution_preview(plan, _priced_policy())

    assert [step["vertical"] for step in preview["steps"]] == ["put", "call"]
    assert [step["side"] for step in preview["steps"]] == ["DEBIT", "DEBIT"]
    assert [step["max_debit"] for step in preview["steps"]] == [1.10, 1.10]


def test_constantstable_mixed_plan_splits_into_left_right_verticals() -> None:
    signal = _signal("examples/sample_constantstable_trade.json", "rapi/GetUltraPureConstantStable")
    plan = build_vertical_bundle_plan(signal, quantity=1)

    preview = build_execution_preview(plan, _priced_policy())

    assert [step["vertical"] for step in preview["steps"]] == ["put", "call"]
    assert [step["side"] for step in preview["steps"]] == ["CREDIT", "DEBIT"]
    assert "min_credit" in preview["steps"][0]
    assert "max_debit" in preview["steps"][1]


def test_full_package_mode_preserves_all_legs_as_one_group() -> None:
    signal = _signal("examples/sample_leoprofit_trade.json", "rapi/GetLeoProfit")
    plan = build_condor_plan(signal, quantity=1, call_multiplier=1)

    preview = build_execution_preview(plan, _priced_policy(mode="full-package"))

    assert preview["dry_run_only"] is True
    assert preview["execution_mode"] == "full-package"
    assert preview["full_package"]["order_type"] == "NET_CREDIT"
    assert preview["full_package"]["min_credit"] == 0.40
    assert len(preview["full_package"]["legs"]) == 4


def test_missing_required_pricing_fails_loudly() -> None:
    signal = _signal("examples/sample_leoprofit_trade.json", "rapi/GetLeoProfit")
    plan = build_condor_plan(signal, quantity=1, call_multiplier=1)
    policy = ExecutionPolicy(profile="empty", execution_mode="verticals")

    with pytest.raises(ValueError, match="min_credit_per_vertical"):
        build_execution_preview(plan, policy)


def test_vertical_preview_includes_partial_fill_warning() -> None:
    signal = _signal("examples/sample_leoprofit_trade.json", "rapi/GetLeoProfit")
    plan = build_condor_plan(signal, quantity=1, call_multiplier=1)

    preview = build_execution_preview(plan, _priced_policy())

    assert preview["dry_run_only"] is True
    assert preview["require_manual_review_after_partial_fill"] is True
    assert any("partial" in warning.lower() for warning in preview["warnings"])


def test_policy_loads_yaml_and_json(tmp_path) -> None:
    yaml_policy = ExecutionPolicy.load("examples/execution_policy.example.yml", profile="michael_default")
    assert yaml_policy.profile == "michael_default"
    assert yaml_policy.execution_mode == "verticals"

    json_path = tmp_path / "policy.json"
    json_path.write_text(json.dumps({"execution_mode": "full-package", "min_credit_full_package": 0.4}))
    json_policy = ExecutionPolicy.load(json_path, profile="default")
    assert json_policy.execution_mode == "full-package"
    assert json_policy.min_credit_full_package == 0.4
