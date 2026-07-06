# Execution Preview

This project still does not place live orders. The execution layer is an
education and planning layer that turns a broker-neutral `StrategyPlan` into a
dry-run execution sequence.

The starter can preview two execution styles:

- `full-package`: keep the full iron condor or vertical bundle together as one
  complex order preview.
- `verticals`: split the structure into individual put/call vertical previews.

The default example profile uses `verticals`, which matches a common manual
workflow: execute one vertical at a time, with user-defined debit/credit limits.

## Full-Package Execution

Full-package execution sends every leg as one package. For a four-leg IC, this
means all four legs are priced together.

Benefits:

- Preserves package pricing.
- Avoids filling one side while the other side remains unfilled.
- Makes the intended max debit or min credit easier to reason about at the
  package level.

Tradeoffs:

- May be harder to fill.
- May require broker-specific complex-order support.
- Broker strategy labels can matter. A ratio condor is not necessarily the same
  thing as a standard iron condor at every broker.

## Vertical-By-Vertical Execution

Vertical execution splits a two-sided package into ordered put/call vertical
steps. For example:

1. Put vertical
2. Call vertical

Benefits:

- Can be simpler to reason about and route.
- Can be easier to fill one side at a time.
- Can support brokers or accounts where full-package complex order support is
  limited.

Risk:

- Partial fills can leave unhedged residual exposure. If the first vertical fills
  and the second vertical does not, the account may hold only half of the
  intended structure.
- The preview therefore includes a partial-fill warning and a manual-review flag.

## Debit And Credit Limits

Execution policy values are intentionally explicit:

- `min_credit_per_vertical`: lowest acceptable credit for each credit vertical.
- `min_credit_full_package`: lowest acceptable credit for a full-package credit
  order.
- `max_debit_per_vertical`: highest acceptable debit for each debit vertical.
- `max_debit_full_package`: highest acceptable debit for a full-package debit
  order.
- `price_step`: price movement per retry/attempt.
- `max_attempts`: maximum previewed order attempts.
- `max_contracts_per_leg`: largest allowed leg size for the preview.
- `reject_stale_signal_minutes`: signal age threshold users can enforce in their
  own broker workflow.

The example policy uses `null` placeholders. That is safe for docs, but not for
execution preview. If a preview needs a credit/debit value and the policy still
has `null`, the CLI fails loudly instead of guessing.

## Example

```bash
leo-go plan \
  --sample examples/sample_leoprofit_trade.json \
  --strategy leoprofit \
  --execution-policy examples/execution_policy.example.yml \
  --profile michael_default
```

That command intentionally fails until real price limits are provided. Use the
example file as a template, not a live policy.
