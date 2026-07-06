from __future__ import annotations

from leo_go_trading.planner import StrategyPlan


def schwab_order_payload(plan: StrategyPlan, limit_price: float) -> dict:
    """Build a Schwab-style complex option order payload preview.

    This function does not submit anything. It only converts the broker-neutral
    plan into the shape expected by Schwab order endpoints.
    """
    if plan.order_type == "MIXED":
        raise ValueError(
            "Mixed debit/credit CS or Novix plans need quote-aware routing. "
            "Preview them as text/JSON, or split the put and call sides in your broker adapter."
        )
    return {
        "orderType": plan.order_type,
        "session": "NORMAL",
        "price": f"{float(limit_price):.2f}",
        "duration": "DAY",
        "orderStrategyType": "SINGLE",
        "complexOrderStrategyType": "IRON_CONDOR",
        "orderLegCollection": [
            {
                "instruction": leg.action,
                "positionEffect": "OPENING",
                "quantity": leg.quantity,
                "instrument": {"symbol": leg.symbol, "assetType": "OPTION"},
            }
            for leg in plan.legs
        ],
    }
