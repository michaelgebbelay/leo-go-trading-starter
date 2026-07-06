from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .brokers.dry_run import preview
from .brokers.ibkr import preview_as_dict as ibkr_preview_as_dict
from .brokers.schwab_payload import schwab_order_payload
from .brokers.tastytrade_payload import tastytrade_order_preview
from .go_api import GammaWizardClient
from .models import TradeSignal
from .planner import build_condor_plan, build_vertical_bundle_plan


def _load_signal(args: argparse.Namespace) -> TradeSignal:
    if args.sample:
        payload = json.loads(Path(args.sample).read_text())
        return TradeSignal.from_payload(payload, endpoint=args.endpoint or "sample")
    endpoint = args.endpoint or os.environ.get("LEO_ENDPOINT", "rapi/GetLeoProfit")
    return GammaWizardClient.from_env().fetch_signal(endpoint)


def cmd_fetch(args: argparse.Namespace) -> int:
    endpoint = args.endpoint or os.environ.get("LEO_ENDPOINT", "rapi/GetLeoProfit")
    payload = GammaWizardClient.from_env().get_json(endpoint)
    print(json.dumps(payload, indent=2, sort_keys=False))
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    signal = _load_signal(args)
    strategy = args.strategy
    if strategy == "auto":
        strategy = "leoprofit" if signal.schema == "LeoProfit-like" else "vertical-bundle"

    if strategy == "leoprofit":
        plan = build_condor_plan(
            signal,
            quantity=args.qty,
            put_width=args.put_width,
            call_width=args.call_width,
            call_multiplier=args.call_mult,
            side_override=args.side,
        )
    elif strategy in {"constantstable", "novix", "vertical-bundle"}:
        plan = build_vertical_bundle_plan(signal, quantity=args.qty, width=args.width)
    else:
        raise ValueError(f"unsupported strategy: {strategy}")

    if args.format == "json":
        print(preview(plan, json_output=True))
    elif args.format == "schwab":
        print(json.dumps(schwab_order_payload(plan, args.limit_price), indent=2, sort_keys=True))
    elif args.format == "ibkr":
        print(json.dumps(ibkr_preview_as_dict(plan), indent=2, sort_keys=True))
    elif args.format == "tastytrade":
        print(json.dumps(tastytrade_order_preview(plan, args.limit_price, args.price_effect), indent=2, sort_keys=True))
    else:
        print(preview(plan))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="leo-go")
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch", help="Fetch and print a raw GO API endpoint payload.")
    fetch.add_argument("--endpoint", default=None, help="Endpoint such as rapi/GetLeoProfit.")
    fetch.set_defaults(func=cmd_fetch)

    plan = sub.add_parser("plan", help="Build a dry-run ticket from a GO API signal.")
    plan.add_argument("--endpoint", default=None, help="Endpoint such as rapi/GetLeoProfit.")
    plan.add_argument("--sample", default=None, help="Path to a saved sample payload.")
    plan.add_argument("--qty", type=int, default=1)
    plan.add_argument(
        "--strategy",
        choices=["auto", "leoprofit", "constantstable", "novix", "vertical-bundle"],
        default="auto",
        help="Signal interpretation. auto uses Cat1/Cat2 for LeoProfit and LeftGo/RightGo for CS/Novix.",
    )
    plan.add_argument("--put-width", type=int, default=20)
    plan.add_argument("--call-width", type=int, default=None)
    plan.add_argument("--call-mult", type=int, default=2)
    plan.add_argument("--width", type=int, default=5, help="Vertical width for ConstantStable/Novix-style signals.")
    plan.add_argument("--side", choices=["AUTO", "CREDIT", "DEBIT"], default="AUTO")
    plan.add_argument("--limit-price", type=float, default=0.05, help="Preview limit price for broker payload formats.")
    plan.add_argument("--price-effect", choices=["Debit", "Credit"], default=None, help="TastyTrade preview price effect for mixed plans.")
    plan.add_argument("--format", choices=["text", "json", "schwab", "tastytrade", "ibkr"], default="text")
    plan.set_defaults(func=cmd_plan)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
