# Strategy Roadmap

The starter kit should stay modular: strategies normalize GO API signals into
broker-neutral tickets, while broker adapters handle order entry for each user's
account.

## Suggested Public Packaging

| Package Area | Status | Notes |
| --- | --- | --- |
| LeoProfit | Starter-supported | IC-only Cat1/Cat2 signals. Generates dry-run ratio-condor tickets. |
| ConstantStable | Starter-supported | LeftGo/RightGo signals. Generates 5-wide put/call vertical bundle tickets. |
| Novix | Starter-supported | Same LeftGo/RightGo interpretation as CS. Generates 5-wide bundle tickets. |
| Schwab adapter | Preview-only | Converts non-mixed plans to Schwab-style payloads. Live submit should remain user-owned. |
| TastyTrade adapter | Preview-supported | Add optional live submit later behind explicit opt-in. |
| LP-confirmed CS side extraction | Separate advanced module | Requires fetching both CS and LeoProfit, schema validation, and structure-aware side extraction. |
| Monthly/streak switch | Research/shadow module | Should not be presented as production-ready. Output a recommendation/shadow state only. |

## Command Shape

Fetch and preview LeoProfit:

```bash
leo-go plan --endpoint rapi/GetLeoProfit --strategy leoprofit --qty 1
```

Fetch and preview ConstantStable:

```bash
leo-go plan --endpoint rapi/GetUltraPureConstantStable --strategy constantstable --qty 1
```

Fetch and preview Novix:

```bash
leo-go plan --endpoint rapi/GetNovix --strategy novix --qty 1
```

Show Schwab-style payload for a full-credit/full-debit ticket:

```bash
leo-go plan --sample examples/sample_novix_trade.json --strategy novix --format schwab --limit-price 1.10
```

Show TastyTrade-style preview:

```bash
leo-go plan --sample examples/sample_novix_trade.json --strategy novix --format tastytrade --limit-price 1.10
```

Mixed risk-reversal tickets are intentionally text/JSON only until a
quote-aware broker adapter decides whether to route as one complex order or split
the put and call sides.

## LP-Confirmed CS Side Extraction

This should be a separate command, for example:

```bash
leo-go confirm-cs \
  --cs-endpoint rapi/GetUltraPureConstantStable \
  --lp-endpoint rapi/GetLeoProfit \
  --qty 1
```

Required behavior:

- Validate the CS payload has `LeftGo` and `RightGo`.
- Validate the LP payload has `Cat1` and `Cat2` and no required dependence on
  CS-style columns.
- Refuse schema mismatches loudly; never silently treat a CS/Novix payload as
  LeoProfit or vice versa.
- If CS and LP are the same IC, trade the full CS IC.
- If CS and LP are opposite ICs, skip.
- If CS is risk-reversal and LP is long IC, trade only the CS buy-premium side.
- If CS is risk-reversal and LP is short IC, trade only the CS sell-premium side.

This is structure-aware side extraction, not simple agreement filtering.

## Monthly Or Streak Switch

Treat this as a shadow/research feature:

```bash
leo-go shadow-switch --state state.json --cs-endpoint ... --lp-endpoint ...
```

It should produce "active model would be X" state and logs, not live orders by
default. The current production doctrine keeps CS baseline as the production
default; switch rules need fresh forward evidence before being promoted.

## Broker Adapters

Use the same strategy ticket for all brokers:

```text
GO API -> TradeSignal -> StrategyPlan -> BrokerAdapter
```

Broker adapters can then expose:

- `preview`: safe text/JSON/payload output.
- `paper`: optional paper-trade submit if the broker supports it.
- `live`: explicit opt-in only, ideally requiring a command flag and environment
  confirmation such as `LEO_GO_ALLOW_LIVE=1`.

Near-term adapter checklist:

- Schwab: payload preview, quote lookup, complex order submit, cancel/replace
  ladder, token refresh docs.
- TastyTrade: quote lookup, complex order submit, cancel/replace ladder, token
  refresh docs.
- IBKR: qualification preview first; live combos require local TWS/Gateway and
  user-specific contract IDs.
