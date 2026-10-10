"""Build, save, load and diff snapshots. A snapshot is all-or-nothing: one failed source, no file."""

import calendar
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from feed import catalog
from feed.sources import ecos, kpx_smp

KST = timezone(timedelta(hours=9))


def period_end(period: str) -> date:
    parts = [int(p) for p in period.split("-")]
    if len(parts) == 3:
        return date(*parts)
    year, month = parts
    return date(year, month, calendar.monthrange(year, month)[1])


def _ecos_window(series: dict, today: date) -> tuple[str, str]:
    if series["cycle"] == "D":
        start = today - timedelta(days=12)  # stays under the sample key's 10-row cap
        return start.strftime("%Y%m%d"), today.strftime("%Y%m%d")
    year, month = today.year, today.month - 6
    if month <= 0:
        year, month = year - 1, month + 12
    return f"{year}{month:02d}", today.strftime("%Y%m")


def _entry(series: dict, observations, source_url: str, today: date, note: str | None = None) -> dict:
    latest_period, latest_value = observations[-1]
    age = (today - period_end(latest_period)).days
    entry = {
        "label": series["label"],
        "unit": series["unit"],
        "source": series["source"],
        "source_url": source_url,
        "grade": "primary",
        "observations": [{"period": p, "value": v} for p, v in observations],
        "latest": {"period": latest_period, "value": latest_value},
        "age_days": age,
        "stale": age > series["max_age_days"],
    }
    if note:
        entry["note"] = note
    return entry


def build(today: date | None = None) -> dict:
    today = today or datetime.now(KST).date()
    series_out = {}

    smp = kpx_smp.fetch()
    for s in catalog.KPX_SMP:
        series_out[s["id"]] = _entry(s, smp[s["region"]], kpx_smp.URL, today)

    for s in catalog.ECOS:
        start, end = _ecos_window(s, today)
        obs, is_sample = ecos.fetch(s["stat"], s["cycle"], start, end, s["item"])
        note = "ECOS sample key (10-row cap)" if is_sample else None
        url = f"{ecos.PAGE_URL} StatisticSearch {s['stat']}/{s['item']}"
        series_out[s["id"]] = _entry(s, obs, url, today, note)

    return {
        "retrieved_at": datetime.now(KST).isoformat(timespec="seconds"),
        "as_of": today.isoformat(),
        "series": series_out,
    }


def save(snapshot: dict, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{snapshot['as_of']}.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
    return path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def latest_before(directory: Path, as_of: str) -> Path | None:
    older = sorted(p for p in directory.glob("*.json") if p.stem < as_of)
    return older[-1] if older else None


def diff(previous: dict, current: dict) -> list[dict]:
    """New periods and, more importantly, revised values for periods already seen."""
    changes = []
    for sid, cur in current["series"].items():
        before = {o["period"]: o["value"] for o in previous["series"].get(sid, {}).get("observations", [])}
        for o in cur["observations"]:
            if o["period"] not in before:
                changes.append({"series": sid, "period": o["period"], "kind": "new", "value": o["value"]})
            elif before[o["period"]] != o["value"]:
                changes.append({"series": sid, "period": o["period"], "kind": "revised",
                                "from": before[o["period"]], "value": o["value"]})
    return changes
