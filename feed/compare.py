"""Check numbers quoted in a draft (from any source) against a primary-source snapshot."""

import csv
from pathlib import Path

TOLERANCE = 0.005  # sources round to 2 decimals


def load_claims(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    required = {"series_id", "period", "claimed_value", "claimed_source", "where"}
    if rows and not required <= rows[0].keys():
        raise ValueError(f"claims file needs columns {sorted(required)}")
    return rows


def check(claims: list[dict], snapshot: dict) -> list[dict]:
    results = []
    for c in claims:
        series = snapshot["series"].get(c["series_id"])
        primary = None
        if series:
            primary = next((o["value"] for o in series["observations"] if o["period"] == c["period"]), None)
        claimed = float(c["claimed_value"])
        if primary is None:
            status, delta = "NOT_IN_SNAPSHOT", None
        else:
            delta = round(claimed - primary, 4)
            status = "MATCH" if abs(delta) <= TOLERANCE else "MISMATCH"
        results.append({**c, "primary_value": primary, "delta": delta, "status": status})
    return results
