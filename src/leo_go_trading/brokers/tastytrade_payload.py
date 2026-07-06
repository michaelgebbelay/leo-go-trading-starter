from __future__ import annotations

from leo_go_trading.planner import StrategyPlan
from leo_go_trading.symbols import compact_osi, tastytrade_symbol_candidates


def _tt_action(action: str) -> str:
    mapping = {
        "BUY_TO_OPEN": "Buy to Open",
        "SELL_TO_OPEN": "Sell to Open",
        "BUY_TO_CLOSE": "Buy to Close",
        "SELL_TO_CLOSE": "Sell to Close",
    }
    return mapping.get(action, action.replace("_", " ").title())


def tastytrade_order_preview(
    plan: StrategyPlan,
    limit_price: float,
    price_effect: str | None = None,
) -> dict:
    """Build a TastyTrade-style complex option order preview.

    This is deliberately a preview shape, not a live submitter. TastyTrade users
    should verify symbol format and account permissions in their own environment
    before turning this into an order placement call.
    """
    effect = price_effect
    if effect is None:
        if plan.order_type == "NET_DEBIT":
            effect = "Debit"
        elif plan.order_type == "NET_CREDIT":
            effect = "Credit"
    if effect is None:
        raise ValueError("Mixed plans require --price-effect Debit or --price-effect Credit for TastyTrade preview.")

    normalized_effect = effect.strip().title()
    if normalized_effect not in {"Debit", "Credit"}:
        raise ValueError("price_effect must be Debit or Credit.")

    return {
        "order-type": "Limit",
        "time-in-force": "Day",
        "price": f"{float(limit_price):.2f}",
        "price-effect": normalized_effect,
        "legs": [
            {
                "instrument-type": "Equity Option",
                "symbol": compact_osi(leg.symbol),
                "action": _tt_action(leg.action),
                "quantity": leg.quantity,
            }
            for leg in plan.legs
        ],
        "metadata": {
            "strategy": plan.structure,
            "source-endpoint": plan.endpoint,
            "preview-only": True,
            "symbol-note": "Verify or resolve exact TastyTrade option symbols from the option-chain endpoint before live submission.",
            "symbol-candidates": {
                leg.symbol: tastytrade_symbol_candidates(leg.symbol)
                for leg in plan.legs
            },
        },
    }
