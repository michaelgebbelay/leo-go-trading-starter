# Leo GO Trading

Leo GO Trading is a working, shareable Python version of the Leo GO trading
workflow. It fetches GO API signals, parses LeoProfit, ConstantStable, and Novix
trade fields, builds SPX option structures, and outputs Schwab/TastyTrade-ready
planning payloads that users can adapt to their own broker setup.

This public version excludes private credentials, account IDs, tokens, and
personal live-submit wiring. Users can plug the broker adapters and execution
policy into their own account setup.

## What It Does

- Authenticates to the GO API with `GW_TOKEN` or `GW_EMAIL` / `GW_PASSWORD`.
- Fetches endpoints such as `rapi/GetLeoProfit` or `rapi/GetLeoCross`.
- Extracts the latest trade row from common GO API response shapes.
- Builds an SPXW iron-condor style ticket from `TDate`, `Limit`, `CLimit`,
  `Cat1`, and `Cat2`.
- Builds ConstantStable / Novix style 5-wide vertical bundle tickets from
  `LeftGo` and `RightGo`.
- Outputs broker-neutral JSON, a human-readable ticket, and Schwab-style
  planning payloads.
- Outputs TastyTrade-style planning payloads.
- Includes an IBKR adapter placeholder showing the fields you need to qualify in
  TWS/Gateway for combo routing.

## Quick Start

```bash
git clone https://github.com/michaelgebbelay/leo-go-trading-starter.git
cd leo-go-trading-starter

python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
```

The CLI auto-loads `.env` from the current directory. Fill in one of these auth
methods:

```bash
GW_TOKEN="paste-token-here"
# or:
GW_EMAIL="you@example.com"
GW_PASSWORD="your-password"
```

Fetch a signal:

```bash
leo-go fetch --endpoint rapi/GetLeoProfit
```

Build a ticket:

```bash
leo-go plan --endpoint rapi/GetLeoProfit --qty 1
```

Build a ConstantStable or Novix ticket:

```bash
leo-go plan --endpoint rapi/GetUltraPureConstantStable --strategy constantstable --qty 1
leo-go plan --endpoint rapi/GetNovix --strategy novix --qty 1
```

Try the included sample without credentials:

```bash
leo-go plan --sample examples/sample_leoprofit_trade.json --qty 1
leo-go plan --sample examples/sample_constantstable_trade.json --strategy constantstable --qty 1
```

See `docs/strategy-roadmap.md` for the recommended path for Schwab, TastyTrade,
LP-confirmed CS, and monthly/shadow switch modules.
See `docs/brokers.md` for broker-specific preview examples.

## Execution Preview

The repo supports two execution styles:

- `full-package`: keep the full iron condor or vertical bundle together as one
  complex order preview.
- `verticals`: split the structure into individual put/call vertical previews.

The default example uses `verticals`, which matches Michael's workflow: execute
one vertical at a time, with user-defined debit/credit limits.

Vertical-by-vertical execution can create a temporary partial position if one
side fills and the other does not. Full-package execution keeps the structure
together but may be harder to fill or require broker-specific routing.

Debit/credit limits, retry steps, max attempts, contract size, and stale-signal
rules are configurable.

```bash
leo-go plan \
  --sample examples/sample_leoprofit_trade.json \
  --strategy leoprofit \
  --execution-policy examples/execution_policy.example.yml \
  --profile michael_default
```

The example policy uses `null` TODO values for price limits, so it fails loudly
until real min-credit/max-debit values are supplied. See `docs/execution.md` for
vertical-by-vertical versus full-package execution notes and partial-fill risks.

## Copy Into Another Project

If you do not want this as its own dependency, vendor the package folder into an
existing bot:

```bash
python scripts/vendor_into_project.py /path/to/my-bot
```

That copies `src/leo_go_trading` into `/path/to/my-bot/leo_go_trading` and leaves
your bot responsible for imports, scheduling, secrets, and broker execution.

## GitHub Actions

The included smoke-test workflow runs the test suite.

For your own private workflow that fetches GO API data, store credentials as
GitHub repository secrets:

- `GW_TOKEN`, or
- `GW_EMAIL` and `GW_PASSWORD`

## Environment Variables

| Variable | Purpose |
| --- | --- |
| `GW_BASE` | GO API base URL. Defaults to `https://gandalf.gammawizard.com`. |
| `GW_TOKEN` | Existing bearer token. |
| `GW_EMAIL` | GO API login email, used when no token is supplied or token expires. |
| `GW_PASSWORD` | GO API login password. |
| `LEO_ENDPOINT` | Default endpoint for the CLI. Defaults to `rapi/GetLeoProfit`. |

## Broker Setup Notes

- Add account-specific guardrails for market hours, duplicate orders, position
  overlap, max loss, max quantity, stale signals, and margin checks.
- Resolve TastyTrade option symbols from the user's own option-chain endpoint;
  public payloads include portable OCC candidates.

## License

MIT. See `LICENSE`.
