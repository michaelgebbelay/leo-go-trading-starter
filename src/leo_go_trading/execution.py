from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import yaml

from .planner import OptionLeg, StrategyPlan


VALID_EXECUTION_MODES = {"verticals", "full-package"}
VALID_VERTICALS = {"put", "call"}


@dataclass(frozen=True)
class ExecutionPolicy:
    profile: str = "default"
    execution_mode: str = "verticals"
    min_credit_per_vertical: float | None = None
    min_credit_full_package: float | None = None
    max_debit_per_vertical: float | None = None
    max_debit_full_package: float | None = None
    price_step: float | None = None
    max_attempts: int | None = None
    vertical_sequence: tuple[str, ...] = ("put", "call")
    stop_if_first_vertical_fails: bool = True
    require_manual_review_after_partial_fill: bool = True
    max_contracts_per_leg: int | None = None
    reject_stale_signal_minutes: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], profile: str = "default") -> "ExecutionPolicy":
        payload = dict(data)
        payload.setdefault("profile", profile)
        if isinstance(payload.get("vertical_sequence"), list):
            payload["vertical_sequence"] = tuple(payload["vertical_sequence"])
        policy = cls(**payload)
        policy.validate_shape()
        return policy

    @classmethod
    def load(cls, path: str | Path, profile: str = "default") -> "ExecutionPolicy":
        policy_path = Path(path)
        if not policy_path.exists():
            raise FileNotFoundError(f"execution policy not found: {policy_path}")
        raw = policy_path.read_text()
        if policy_path.suffix.lower() == ".json":
            data = json.loads(raw)
        else:
            data = yaml.safe_load(raw) or {}
        if not isinstance(data, dict):
            raise ValueError("execution policy must be a mapping.")

        profiles = data.get("profiles")
        if isinstance(profiles, dict):
            if profile not in profiles:
                raise ValueError(f"profile {profile!r} not found in {policy_path}")
            selected = profiles[profile]
        else:
            selected = data
        if not isinstance(selected, dict):
            raise ValueError(f"profile {profile!r} must be a mapping.")
        return cls.from_dict(selected, profile=profile)

    def with_mode(self, execution_mode: str | None) -> "ExecutionPolicy":
        if not execution_mode:
            return self
        updated = replace(self, execution_mode=execution_mode)
        updated.validate_shape()
        return updated

    def validate_shape(self) -> None:
        if self.execution_mode not in VALID_EXECUTION_MODES:
            raise ValueError(f"execution_mode must be one of {sorted(VALID_EXECUTION_MODES)}")
        unknown = [item for item in self.vertical_sequence if item not in VALID_VERTICALS]
        if unknown:
            raise ValueError(f"vertical_sequence contains unknown entries: {unknown}")
        if len(set(self.vertical_sequence)) != len(self.vertical_sequence):
            raise ValueError("vertical_sequence must not contain duplicates.")
        if self.max_attempts is not None and self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1 when provided.")
        if self.max_contracts_per_leg is not None and self.max_contracts_per_leg < 1:
            raise ValueError("max_contracts_per_leg must be >= 1 when provided.")

    def require_limit_for_side(self, side: str, scope: str) -> dict[str, float]:
        side_value = side.upper()
        if scope == "vertical":
            if side_value == "CREDIT":
                return {"min_credit": _required(self.min_credit_per_vertical, "min_credit_per_vertical")}
            if side_value == "DEBIT":
                return {"max_debit": _required(self.max_debit_per_vertical, "max_debit_per_vertical")}
        if scope == "full-package":
            if side_value == "NET_CREDIT":
                return {"min_credit": _required(self.min_credit_full_package, "min_credit_full_package")}
            if side_value == "NET_DEBIT":
                return {"max_debit": _required(self.max_debit_full_package, "max_debit_full_package")}
            if side_value == "MIXED":
                return {
                    "min_credit": _required(self.min_credit_full_package, "min_credit_full_package"),
                    "max_debit": _required(self.max_debit_full_package, "max_debit_full_package"),
                }
        raise ValueError(f"unsupported pricing side/scope: {side} / {scope}")


def _required(value: float | None, field: str) -> float:
    if value is None:
        raise ValueError(f"execution policy requires {field}; fill the TODO/null value before execution preview.")
    return float(value)


def build_execution_preview(plan: StrategyPlan, policy: ExecutionPolicy) -> dict[str, Any]:
    policy.validate_shape()
    _validate_contract_limit(plan, policy)
    if policy.execution_mode == "full-package":
        return _full_package_preview(plan, policy)
    return _verticals_preview(plan, policy)


def _full_package_preview(plan: StrategyPlan, policy: ExecutionPolicy) -> dict[str, Any]:
    limits = policy.require_limit_for_side(plan.order_type, "full-package")
    return {
        "dry_run_only": True,
        "profile": policy.profile,
        "execution_mode": "full-package",
        "warnings": [
            "Full-package execution preserves package pricing but is broker-specific and may be harder to fill.",
            "This preview does not place orders.",
        ],
        "full_package": {
            "order_type": plan.order_type,
            "structure": plan.structure,
            **limits,
            "price_step": policy.price_step,
            "max_attempts": policy.max_attempts,
            "legs": [_leg_dict(leg) for leg in plan.legs],
        },
    }


def _verticals_preview(plan: StrategyPlan, policy: ExecutionPolicy) -> dict[str, Any]:
    verticals = _split_verticals(plan)
    steps = []
    for vertical_name in policy.vertical_sequence:
        if vertical_name not in verticals:
            continue
        vertical = verticals[vertical_name]
        limits = policy.require_limit_for_side(vertical["side"], "vertical")
        steps.append(
            {
                "step": len(steps) + 1,
                "vertical": vertical_name,
                "side": vertical["side"],
                **limits,
                "price_step": policy.price_step,
                "max_attempts": policy.max_attempts,
                "stop_if_first_vertical_fails": policy.stop_if_first_vertical_fails and len(steps) == 0,
                "legs": [_leg_dict(leg) for leg in vertical["legs"]],
            }
        )

    return {
        "dry_run_only": True,
        "profile": policy.profile,
        "execution_mode": "verticals",
        "warnings": [
            "Vertical-by-vertical execution can partially fill one side and leave unhedged residual exposure.",
            "Manual review is required after any partial fill before continuing.",
            "This preview does not place orders.",
        ],
        "require_manual_review_after_partial_fill": policy.require_manual_review_after_partial_fill,
        "steps": steps,
    }


def _split_verticals(plan: StrategyPlan) -> dict[str, dict[str, Any]]:
    grouped = {
        "put": tuple(leg for leg in plan.legs if leg.right == "P"),
        "call": tuple(leg for leg in plan.legs if leg.right == "C"),
    }
    out: dict[str, dict[str, Any]] = {}
    for name, legs in grouped.items():
        if not legs:
            continue
        if len(legs) != 2:
            raise ValueError(f"{name} vertical requires exactly 2 legs, got {len(legs)}")
        out[name] = {"side": _vertical_side(name, legs), "legs": legs}
    return out


def _vertical_side(name: str, legs: tuple[OptionLeg, OptionLeg]) -> str:
    lower, higher = sorted(legs, key=lambda leg: leg.strike)
    inner = higher if name == "put" else lower
    outer = lower if name == "put" else higher
    if inner.action == "SELL_TO_OPEN" and outer.action == "BUY_TO_OPEN":
        return "CREDIT"
    if inner.action == "BUY_TO_OPEN" and outer.action == "SELL_TO_OPEN":
        return "DEBIT"
    raise ValueError(f"could not determine {name} vertical side from leg actions.")


def _validate_contract_limit(plan: StrategyPlan, policy: ExecutionPolicy) -> None:
    if policy.max_contracts_per_leg is None:
        return
    too_large = [leg for leg in plan.legs if leg.quantity > int(policy.max_contracts_per_leg)]
    if too_large:
        symbols = ", ".join(leg.symbol.strip() for leg in too_large)
        raise ValueError(f"plan exceeds max_contracts_per_leg={policy.max_contracts_per_leg}: {symbols}")


def _leg_dict(leg: OptionLeg) -> dict[str, Any]:
    return asdict(leg)
