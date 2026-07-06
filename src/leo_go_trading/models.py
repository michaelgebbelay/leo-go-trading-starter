from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


def _find_trade(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        if "Trade" in payload:
            trade = payload["Trade"]
            if isinstance(trade, list) and trade:
                return trade[-1] if isinstance(trade[-1], dict) else {}
            return trade if isinstance(trade, dict) else {}
        for value in payload.values():
            if isinstance(value, (dict, list)):
                found = _find_trade(value)
                if found:
                    return found
    if isinstance(payload, list):
        for item in reversed(payload):
            found = _find_trade(item)
            if found:
                return found
    return {}


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class TradeSignal:
    endpoint: str
    tdate: date
    short_put: float
    short_call: float
    cat1: float | None = None
    cat2: float | None = None
    left_go: float | None = None
    right_go: float | None = None
    raw: dict[str, Any] | None = None

    @property
    def schema(self) -> str:
        if self.left_go is not None and self.right_go is not None:
            if "novix" in self.endpoint.lower():
                return "Novix-like"
            return "ConstantStable-like"
        if self.cat1 is not None and self.cat2 is not None:
            return "LeoProfit-like"
        return "Unknown"

    @property
    def side(self) -> str:
        if self.cat1 is not None and self.cat2 is not None and self.cat2 < self.cat1:
            return "DEBIT"
        if self.left_go is not None and self.right_go is not None:
            if self.left_go > 0 and self.right_go > 0:
                return "DEBIT"
            if self.left_go < 0 and self.right_go < 0:
                return "CREDIT"
            return "MIXED"
        return "CREDIT"

    @property
    def structure(self) -> str:
        if self.cat1 is not None and self.cat2 is not None:
            return "IC_LONG" if self.cat1 > self.cat2 else "IC_SHORT"
        if self.left_go is not None and self.right_go is not None:
            if self.left_go > 0 and self.right_go > 0:
                return "IC_LONG"
            if self.left_go < 0 and self.right_go < 0:
                return "IC_SHORT"
            if self.left_go > 0 and self.right_go < 0:
                return "RR_LONG_PUT"
            return "RR_LONG_CALL"
        return "UNKNOWN"

    @classmethod
    def from_payload(cls, payload: Any, endpoint: str = "") -> "TradeSignal":
        trade = _find_trade(payload)
        if not trade:
            raise ValueError("Could not find a Trade object in the GO API payload.")

        tdate_raw = str(trade.get("TDate") or trade.get("tdate") or "")[:10]
        short_put = _float_or_none(trade.get("Limit"))
        short_call = _float_or_none(trade.get("CLimit"))
        if not tdate_raw or short_put is None or short_call is None:
            raise ValueError("Trade must include TDate, Limit, and CLimit.")

        return cls(
            endpoint=endpoint,
            tdate=date.fromisoformat(tdate_raw),
            short_put=short_put,
            short_call=short_call,
            cat1=_float_or_none(trade.get("Cat1")),
            cat2=_float_or_none(trade.get("Cat2")),
            left_go=_float_or_none(trade.get("LeftGo")),
            right_go=_float_or_none(trade.get("RightGo")),
            raw=trade,
        )
