"""Bank of Korea ECOS Open API (StatisticSearch).

Set ECOS_API_KEY in the environment. Without it the public `sample` key is used,
which ECOS caps at 10 rows per call; the snapshot records which key type was used.
"""

import json
import os

from feed import SourceError
from feed.http import get

BASE = "https://ecos.bok.or.kr/api/StatisticSearch"
PAGE_URL = "https://ecos.bok.or.kr/"


def api_key() -> tuple[str, bool]:
    key = os.environ.get("ECOS_API_KEY", "").strip()
    return (key, False) if key else ("sample", True)


def _period(time: str, cycle: str) -> str:
    if cycle == "D" and len(time) == 8:
        return f"{time[:4]}-{time[4:6]}-{time[6:]}"
    if cycle == "M" and len(time) == 6:
        return f"{time[:4]}-{time[4:]}"
    raise SourceError(f"ecos: cannot read period {time!r} for cycle {cycle}")


def parse(payload: str, stat: str, item: str, cycle: str) -> list[tuple[str, float]]:
    data = json.loads(payload)
    if "StatisticSearch" not in data:
        result = data.get("RESULT", {})
        raise SourceError(f"ecos {stat}/{item}: {result.get('CODE')} {result.get('MESSAGE')}")
    rows = data["StatisticSearch"].get("row", [])
    out = []
    for row in rows:
        if row.get("STAT_CODE") != stat or row.get("ITEM_CODE1") != item:
            raise SourceError(f"ecos: row for {row.get('STAT_CODE')}/{row.get('ITEM_CODE1')}, asked {stat}/{item}")
        out.append((_period(row["TIME"], cycle), float(row["DATA_VALUE"])))
    if not out:
        raise SourceError(f"ecos {stat}/{item}: empty result")
    return out


def fetch(stat: str, cycle: str, start: str, end: str, item: str) -> tuple[list[tuple[str, float]], bool]:
    key, is_sample = api_key()
    rows = 10 if is_sample else 100
    url = f"{BASE}/{key}/json/kr/1/{rows}/{stat}/{cycle}/{start}/{end}/{item}"
    obs = parse(get(url), stat, item, cycle)
    if len(obs) >= rows:
        raise SourceError(f"ecos {stat}/{item}: hit the {rows}-row cap, latest value may be cut off; narrow the window")
    return obs, is_sample
