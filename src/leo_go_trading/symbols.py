from __future__ import annotations

from datetime import date


def expiry_yymmdd(expiry: date) -> str:
    return f"{expiry:%y%m%d}"


def osi_symbol(root: str, expiry: date, right: str, strike: float) -> str:
    clean_root = root.upper().lstrip(".")[:6]
    right_value = right.upper()
    if right_value not in {"C", "P"}:
        raise ValueError("right must be C or P")
    mills = int(round(float(strike) * 1000))
    return f"{clean_root:<6}{expiry_yymmdd(expiry)}{right_value}{mills:08d}"


def strike_from_osi(symbol: str) -> float:
    return int(symbol[-8:]) / 1000.0


def compact_osi(symbol: str) -> str:
    return (symbol or "").strip().replace(" ", "")


def tastytrade_symbol_candidates(symbol: str) -> list[str]:
    compact = compact_osi(symbol)
    candidates = []
    if compact:
        candidates.append(compact)
        if compact.startswith("SPXW"):
            candidates.append("SPX" + compact[4:])
    return list(dict.fromkeys(candidates))
