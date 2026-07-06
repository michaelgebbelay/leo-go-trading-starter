# Broker Adapter Notes

The public starter kit has one strategy layer and multiple broker presentation
layers:

```text
GO API signal -> StrategyPlan -> Schwab / TastyTrade / IBKR adapter
```

## Current Status

| Broker | Status | Command |
| --- | --- | --- |
| Schwab | Payload preview for non-mixed complex orders | `--format schwab` |
| TastyTrade | Ticket preview for complex orders | `--format tastytrade` |
| IBKR | Contract qualification preview | `--format ibkr` |

All broker outputs are preview-only. They do not submit orders.

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
Schwab payload preview. A real adapter should use live quotes to decide whether
the combined package routes as net debit, net credit, or split verticals.

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

Before live use, users need their own:

- TastyTrade login/token refresh.
- Account selection.
- OCC symbol verification.
- Quote lookup.
- Buying-power and max-loss checks.
- Duplicate-order and existing-position checks.
- Cancel/replace ladder or single limit policy.

## IBKR

The IBKR preview intentionally stops before creating an order. IBKR combo orders
need contract IDs from the user's own TWS/Gateway session.
