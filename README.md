# infra-assumption-feed

[![CI](https://github.com/ITJHIT/infra-assumption-feed/actions/workflows/ci.yml/badge.svg)](https://github.com/ITJHIT/infra-assumption-feed/actions/workflows/ci.yml)

Pulls the market inputs of a Korean infrastructure model (power prices, policy rate, government and corporate bond yields) straight from the institutions that publish them, and stamps every number with its source, period and age.

## The job it replaces

Every project-finance model starts with an assumption sheet, and somebody has to keep it current: look up last month's wholesale power price, today's treasury yields, the policy rate. In practice that often means copying a figure from whichever article or blog comes up first. The figure looks right, nobody traces it, and it ends up in the model.

This tool does that update in one command, from primary sources only. It also checks the numbers already sitting in a draft.

```bash
python -m feed fetch                                   # pull everything, save snapshots/<date>.json
python -m feed table                                   # print the assumption table
python -m feed compare examples/claims_solar_draft.csv # check a draft's numbers against primary data
```

## What it found on its first run

A draft analysis of a solar project quoted three monthly power prices. Two of them came from an industry blog, and the blog's figures were wrong:

| Period | Draft said | Source in draft | Power exchange says | Delta | Status |
|---|---|---|---|---|---|
| 2026-01 | 103.54 | search summary of the exchange's table | 103.54 | 0.00 | MATCH |
| 2026-08 | 148.91 | industry blog | 148.39 | +0.52 | MISMATCH |
| 2026-09 | 116.74 | industry blog | 119.02 | −2.28 | MISMATCH |

The draft's headline, "prices fell more than 31 won in a month", rested on the blog's numbers. The primary data says the fall was 29.37 won. The story still holds, but the number in it was wrong.

## Sources

| Series | Publisher | Access |
|---|---|---|
| System marginal price (SMP), mainland and Jeju, monthly | Korea Power Exchange | public statistics page, no key |
| Bank of Korea base rate | Bank of Korea, ECOS | Open API |
| Korea Treasury Bond 3Y, 5Y, 10Y yields | Bank of Korea, ECOS | Open API |
| Corporate bond 3Y (AA−) yield | Bank of Korea, ECOS | Open API |

ECOS reads its key from the `ECOS_API_KEY` environment variable. Without one, the tool uses ECOS's public `sample` key, which is capped at 10 rows per call, and records that in the snapshot. Keys are never written to disk.

## Design choices

- **No fallback values.** If any source fails, the run stops and no snapshot is written. A model input that silently went stale is worse than a run that fails loudly.
- **Shape checks, not guesses.** The power exchange publishes an HTML table, not an API. If its header, region labels or row shape change, parsing stops instead of reading the wrong cell.
- **Plausibility bounds.** A price outside 0–1,000 KRW/kWh stops the run.
- **Row-cap guard.** If a response hits the API's row limit, the latest value may have been cut off, so the run stops.
- **Revisions are reported.** Each run is diffed against the previous snapshot. A value that changed for a period already seen is printed as `REVISED`, separately from new periods.
- **Staleness is explicit.** Each series has a maximum age (7 days for daily yields, 45 days for monthly series). Stale series are flagged, and the run exits with a non-zero code.

## How it is verified

Thirteen offline tests run in CI against real responses saved on 2026-10-10 ([`tests/fixtures/`](tests/fixtures/)). They check known values, a renamed region, a missing region, a changed header, an implausible price, an ECOS error response, a response for the wrong series, staleness, the all-or-nothing write, revision detection, and the claim check.

```bash
pip install pytest
python -m pytest -q
```

## Not yet covered

- **REC spot prices.** The power exchange publishes them through the public data portal API, which needs a registered key. They will be added once the response format can be verified against a live call.
- **Monthly averages only for SMP.** The hourly series exists, but the models this feeds use monthly or annual prices.

## Related

[infra-im-harness](https://github.com/ITJHIT/infra-im-harness) holds the verification gates this tool serves. Its `assumption-trace` gate requires a primary source, a base year and a grade for every input. This tool produces exactly that, automatically.
