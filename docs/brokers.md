# Broker Adapter Notes

Leo GO Trading has one strategy layer and multiple broker presentation layers:

```text
GO API signal -> StrategyPlan -> Schwab / TastyTrade / IBKR adapter
```

## Current Status

| Broker | Status | Command |
| --- | --- | --- |
| Schwab | Planning payload for non-mixed complex orders | `--format schwab` |
| TastyTrade | Planning payload for complex orders | `--format tastytrade` |
| IBKR | Contract qualification payload | `--format ibkr` |

## Schwab

Example:

```bash
leo-go plan \
  --sample examples/sample_novix_trade.json \
  --strategy novix \
  --format schwab \
  --limit-price 1.10
```

Mixed ConstantStable/Novix risk-reversal tickets currently raise an error in the
Schwab payload builder. A Schwab-specific adapter should use live quotes to
decide whether the combined package routes as net debit, net credit, or split
verticals.

## TastyTrade

Example:

```bash
leo-go plan \
  --sample examples/sample_novix_trade.json \
  --strategy novix \
  --format tastytrade \
  --limit-price 1.10
```

For mixed risk-reversal tickets, provide a price effect:

```bash
leo-go plan \
  --sample examples/sample_constantstable_trade.json \
  --strategy constantstable \
  --format tastytrade \
  --limit-price 0.20 \
  --price-effect Credit
```

For account-specific use, users provide their own:

- TastyTrade login/token refresh.
- Account selection.
- OCC symbol verification.
- Option-chain symbol resolution for exact TastyTrade order symbols.
- Quote lookup.
- Buying-power and max-loss checks.
- Duplicate-order and existing-position checks.
- Cancel/replace ladder or single limit policy.

## IBKR

IBKR combo orders need contract IDs from the user's own TWS/Gateway session.
