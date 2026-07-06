from __future__ import annotations

from typing import Protocol

from leo_go_trading.planner import StrategyPlan


class BrokerAdapter(Protocol):
    def preview(self, plan: StrategyPlan) -> str:
        """Return a human-readable order preview."""


def human_ticket(plan: StrategyPlan) -> str:
    lines = [
        f"{plan.side} {plan.structure} {plan.order_type}",
        f"qty={plan.quantity} put_width={plan.put_width} call_width={plan.call_width} call_mult={plan.call_multiplier}",
    ]
    for leg in plan.legs:
        lines.append(f"- {leg.action:<12} x{leg.quantity:<3} {leg.symbol} {leg.right}{leg.strike:g} exp={leg.expiry}")
    return "\n".join(lines)
