# Leo GO Trading Starter

Small, broker-agnostic Python starter kit for reading Leo/GammaWizard GO API trade
signals and turning them into reviewable SPX option tickets.

This project is intentionally a starter kit, not a black-box trading bot. It
defaults to dry-run output and refuses to place live orders. Wire broker-specific
execution only after you have reviewed the generated ticket, tested in paper
trading, and accepted the risk.

## What It Does

- Authenticates to the GO API with `GW_TOKEN` or `GW_EMAIL` / `GW_PASSWORD`.
- Fetches endpoints such as `rapi/GetLeoProfit` or `rapi/GetLeoCross`.
- Extracts the latest trade row from common GO API response shapes.
- Builds an SPXW iron-condor style ticket from `TDate`, `Limit`, `CLimit`,
  `Cat1`, and `Cat2`.
- Builds ConstantStable / Novix style 5-wide vertical bundle tickets from
  `LeftGo` and `RightGo`.
- Outputs broker-neutral JSON, a human-readable ticket, and optional Schwab-style
  order payload previews.
- Outputs TastyTrade-style ticket previews.
- Includes an IBKR adapter placeholder showing the fields you need to qualify in
  TWS/Gateway before live execution.

## Quick Start

```bash
git clone https://github.com/michaelgebbelay/leo-go-trading-starter.git
cd leo-go-trading-starter

python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
```

Then set one of these auth methods:

```bash
export GW_TOKEN="paste-token-here"
# or
export GW_EMAIL="you@example.com"
export GW_PASSWORD="your-password"
```

Fetch a signal:

```bash
leo-go fetch --endpoint rapi/GetLeoProfit
```

Build a dry-run ticket:

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

## Copy Into Another Project

If you do not want this as its own dependency, vendor the package folder into an
existing bot:

```bash
python scripts/vendor_into_project.py /path/to/my-bot
```

That copies `src/leo_go_trading` into `/path/to/my-bot/leo_go_trading` and leaves
your bot responsible for imports, scheduling, secrets, and broker execution.

## GitHub Actions

The included smoke-test workflow only runs tests. It does not fetch GO API data or
place orders.

For your own private workflow that fetches GO API data, store credentials as
GitHub repository secrets:

- `GW_TOKEN`, or
- `GW_EMAIL` and `GW_PASSWORD`

Do not commit `.env`, token files, account numbers, broker app secrets, or order
logs that contain account identifiers.

## Environment Variables

| Variable | Purpose |
| --- | --- |
| `GW_BASE` | GO API base URL. Defaults to `https://gandalf.gammawizard.com`. |
| `GW_TOKEN` | Existing bearer token. |
| `GW_EMAIL` | GO API login email, used when no token is supplied or token expires. |
| `GW_PASSWORD` | GO API login password. |
| `LEO_ENDPOINT` | Default endpoint for the CLI. Defaults to `rapi/GetLeoProfit`. |

## Safety Notes

- This is educational automation scaffolding, not financial advice.
- Generated orders may be wrong for your account, broker, permissions, data feed,
  time zone, margin model, or option symbol convention.
- Start with read-only fetches and dry-run tickets.
- Paper trade before live trading.
- Add your own guardrails for market hours, duplicate orders, position overlap,
  max loss, max quantity, stale signals, and account-specific margin checks.

## License

MIT. See `LICENSE`.
