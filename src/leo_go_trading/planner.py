from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .models import TradeSignal
from .symbols import osi_symbol


@dataclass(frozen=True)
class OptionLeg:
    action: str
    symbol: str
    quantity: int
    right: str
    strike: float
    expiry: str


@dataclass(frozen=True)
class StrategyPlan:
    endpoint: str
    side: str
    order_type: str
    structure: str
    quantity: int
    call_multiplier: int
    put_width: int
    call_width: int
    legs: tuple[OptionLeg, ...]
    source_trade: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["legs"] = [asdict(leg) for leg in self.legs]
        return data


def _round_to_5(width: int | float) -> int:
    value = int(round(float(width) / 5.0) * 5)
    return max(5, value)


def build_condor_plan(
    signal: TradeSignal,
    quantity: int = 1,
    put_width: int = 20,
    call_width: int | None = None,
    call_multiplier: int = 2,
    side_override: str = "AUTO",
    root: str = "SPXW",
) -> StrategyPlan:
    if signal.cat1 is None or signal.cat2 is None:
        raise ValueError("LeoProfit planning requires Cat1 and Cat2.")
    side = signal.side
    override = (side_override or "AUTO").upper()
    if override in {"CREDIT", "DEBIT"}:
        side = override
    elif override != "AUTO":
        raise ValueError("side_override must be AUTO, CREDIT, or DEBIT.")

    qty = max(1, int(quantity))
    put_w = _round_to_5(put_width)
    call_w = _round_to_5(call_width if call_width is not None else max(5, put_w // 2))
    mult = max(1, int(call_multiplier))

    short_put = float(signal.short_put)
    short_call = float(signal.short_call)

    if side == "CREDIT":
        buy_put_strike = short_put - put_w
        sell_put_strike = short_put
        sell_call_strike = short_call
        buy_call_strike = short_call + call_w
        order_type = "NET_CREDIT"
        structure = "CONDOR_RATIO" if mult > 1 else "CONDOR"
        legs = (
            OptionLeg("BUY_TO_OPEN", osi_symbol(root, signal.tdate, "P", buy_put_strike), qty, "P", buy_put_strike, signal.tdate.isoformat()),
            OptionLeg("SELL_TO_OPEN", osi_symbol(root, signal.tdate, "P", sell_put_strike), qty, "P", sell_put_strike, signal.tdate.isoformat()),
            OptionLeg("SELL_TO_OPEN", osi_symbol(root, signal.tdate, "C", sell_call_strike), qty * mult, "C", sell_call_strike, signal.tdate.isoformat()),
            OptionLeg("BUY_TO_OPEN", osi_symbol(root, signal.tdate, "C", buy_call_strike), qty * mult, "C", buy_call_strike, signal.tdate.isoformat()),
        )
    else:
        # Long/debit condor orientation: buy inner wings, sell outer wings.
        debit_width = 5
        buy_put_strike = short_put
        sell_put_strike = short_put - debit_width
        sell_call_strike = short_call + debit_width
        buy_call_strike = short_call
        put_w = debit_width
        call_w = debit_width
        mult = 1
        order_type = "NET_DEBIT"
        structure = "CONDOR"
        legs = (
            OptionLeg("BUY_TO_OPEN", osi_symbol(root, signal.tdate, "P", buy_put_strike), qty, "P", buy_put_strike, signal.tdate.isoformat()),
            OptionLeg("SELL_TO_OPEN", osi_symbol(root, signal.tdate, "P", sell_put_strike), qty, "P", sell_put_strike, signal.tdate.isoformat()),
            OptionLeg("SELL_TO_OPEN", osi_symbol(root, signal.tdate, "C", sell_call_strike), qty, "C", sell_call_strike, signal.tdate.isoformat()),
            OptionLeg("BUY_TO_OPEN", osi_symbol(root, signal.tdate, "C", buy_call_strike), qty, "C", buy_call_strike, signal.tdate.isoformat()),
        )

    return StrategyPlan(
        endpoint=signal.endpoint,
        side=side,
        order_type=order_type,
        structure=structure,
        quantity=qty,
        call_multiplier=mult,
        put_width=put_w,
        call_width=call_w,
        legs=legs,
        source_trade=signal.raw,
    )


def build_vertical_bundle_plan(
    signal: TradeSignal,
    quantity: int = 1,
    width: int = 5,
    root: str = "SPXW",
) -> StrategyPlan:
    """Build a 5-wide CS/Novix-style put+call vertical bundle.

    ConstantStable and Novix use independent put/call directions from
    LeftGo/RightGo. The result may be a full long IC, full short IC, or mixed
    risk-reversal style structure.
    """
    if signal.left_go is None or signal.right_go is None:
        raise ValueError("ConstantStable/Novix planning requires LeftGo and RightGo.")

    qty = max(1, int(quantity))
    vert_w = _round_to_5(width)
    short_put = float(signal.short_put)
    short_call = float(signal.short_call)

    put_buy = signal.left_go > 0
    call_buy = signal.right_go > 0

    if put_buy:
        put_legs = (
            OptionLeg("BUY_TO_OPEN", osi_symbol(root, signal.tdate, "P", short_put), qty, "P", short_put, signal.tdate.isoformat()),
            OptionLeg("SELL_TO_OPEN", osi_symbol(root, signal.tdate, "P", short_put - vert_w), qty, "P", short_put - vert_w, signal.tdate.isoformat()),
        )
    else:
        put_legs = (
            OptionLeg("SELL_TO_OPEN", osi_symbol(root, signal.tdate, "P", short_put), qty, "P", short_put, signal.tdate.isoformat()),
            OptionLeg("BUY_TO_OPEN", osi_symbol(root, signal.tdate, "P", short_put - vert_w), qty, "P", short_put - vert_w, signal.tdate.isoformat()),
        )

    if call_buy:
        call_legs = (
            OptionLeg("BUY_TO_OPEN", osi_symbol(root, signal.tdate, "C", short_call), qty, "C", short_call, signal.tdate.isoformat()),
            OptionLeg("SELL_TO_OPEN", osi_symbol(root, signal.tdate, "C", short_call + vert_w), qty, "C", short_call + vert_w, signal.tdate.isoformat()),
        )
    else:
        call_legs = (
            OptionLeg("SELL_TO_OPEN", osi_symbol(root, signal.tdate, "C", short_call), qty, "C", short_call, signal.tdate.isoformat()),
            OptionLeg("BUY_TO_OPEN", osi_symbol(root, signal.tdate, "C", short_call + vert_w), qty, "C", short_call + vert_w, signal.tdate.isoformat()),
        )

    if put_buy and call_buy:
        order_type = "NET_DEBIT"
    elif (not put_buy) and (not call_buy):
        order_type = "NET_CREDIT"
    else:
        order_type = "MIXED"

    return StrategyPlan(
        endpoint=signal.endpoint,
        side=signal.side,
        order_type=order_type,
        structure=signal.structure,
        quantity=qty,
        call_multiplier=1,
        put_width=vert_w,
        call_width=vert_w,
        legs=put_legs + call_legs,
        source_trade=signal.raw,
    )
