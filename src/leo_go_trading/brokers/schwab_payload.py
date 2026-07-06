from __future__ import annotations

from leo_go_trading.planner import StrategyPlan


def schwab_order_payload(plan: StrategyPlan, limit_price: float) -> dict:
    """Build a Schwab-style complex option order payload preview.

    This function does not submit anything. It only converts the broker-neutral
    plan into the shape expected by Schwab order endpoints.
    """
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
