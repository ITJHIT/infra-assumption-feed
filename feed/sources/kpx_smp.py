"""Monthly SMP (system marginal price) from the Korea Power Exchange's public statistics page.

The page is an HTML table: one row group per region, one row per year, one column per month.
No API key is needed. If the table's shape changes, parsing stops with SourceError
rather than guessing which cell is which.
"""

import re
from html.parser import HTMLParser

from feed import SourceError
from feed.http import get

URL = "https://new.kpx.or.kr/smpMonthly.es?mid=a10606080300&device=pc"

REGIONS = {"육지 SMP": "mainland", "제주 SMP": "jeju", "통합 SMP": "integrated"}
MONTHS = [f"{m}월" for m in range(1, 13)]
YEAR_CELL = re.compile(r"^(\d{2})년$")


class _TableRows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self._row, self._cell = [], None, None
        self._tables = 0

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._tables += 1
        elif tag == "tr" and self._tables == 1:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None:
            self._row.append("".join(self._cell).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def parse(html: str) -> dict[str, list[tuple[str, float]]]:
    """Return {region: [(YYYY-MM, value), ...]} in table order."""
    parser = _TableRows()
    parser.feed(html)
    if not parser.rows:
        raise SourceError("kpx_smp: no table rows found")

    header, body = parser.rows[0], parser.rows[1:]
    if header[1:] != MONTHS:
        raise SourceError(f"kpx_smp: unexpected header {header!r}")

    out: dict[str, list[tuple[str, float]]] = {}
    region = None
    for row in body:
        if row and row[0] in REGIONS:
            region, row = REGIONS[row[0]], row[1:]
        if region is None:
            raise SourceError(f"kpx_smp: data row before any region label: {row!r}")
        year_match = YEAR_CELL.match(row[0]) if row else None
        if not year_match or len(row) != 13:
            raise SourceError(f"kpx_smp: unexpected row shape: {row!r}")
        year = 2000 + int(year_match.group(1))
        for month, cell in enumerate(row[1:], start=1):
            if cell == "":
                continue  # month not published yet
            try:
                value = float(cell.replace(",", ""))
            except ValueError as exc:
                raise SourceError(f"kpx_smp: non-numeric cell {cell!r}") from exc
            if not 0 < value < 1000:
                raise SourceError(f"kpx_smp: implausible SMP {value} KRW/kWh")
            out.setdefault(region, []).append((f"{year}-{month:02d}", value))

    missing = set(REGIONS.values()) - set(out)
    if missing:
        raise SourceError(f"kpx_smp: regions missing from table: {sorted(missing)}")
    return out


def fetch() -> dict[str, list[tuple[str, float]]]:
    return parse(get(URL))
