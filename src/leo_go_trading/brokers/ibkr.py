from __future__ import annotations

from dataclasses import asdict, dataclass

from leo_go_trading.planner import StrategyPlan


@dataclass(frozen=True)
class IbkrPreview:
    symbol: str
    exchange: str
    currency: str
    legs_to_qualify: list[dict]
    combo_hint: str


def build_ibkr_preview(plan: StrategyPlan, exchange: str = "CBOE", currency: str = "USD") -> IbkrPreview:
    """Return the IBKR contract fields a user must qualify in TWS/Gateway.

    IBKR combo placement requires broker-side contract IDs. Those IDs should be
    obtained from the user's own paper or live TWS/Gateway session before order
    placement. This helper avoids pretending a portable repo can safely place
    account-specific combo orders out of the box.
    """
    legs = []
    for leg in plan.legs:
        legs.append(
            {
                "symbol": "SPX",
                "lastTradeDateOrContractMonth": leg.expiry.replace("-", ""),
                "strike": leg.strike,
                "right": leg.right,
                "exchange": exchange,
                "currency": currency,
                "action": "BUY" if leg.action.startswith("BUY") else "SELL",
                "ratio": leg.quantity,
            }
        )
    return IbkrPreview(
        symbol="SPX",
        exchange=exchange,
        currency=currency,
        legs_to_qualify=legs,
        combo_hint="Use ib_insync.IB.qualifyContracts for each option, then create a BAG combo from the returned conIds.",
    )


def preview_as_dict(plan: StrategyPlan) -> dict:
    return asdict(build_ibkr_preview(plan))
