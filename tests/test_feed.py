"""Offline tests. Fixtures are real responses saved on 2026-10-10."""

import json
from datetime import date
from pathlib import Path

import pytest

from feed import SourceError, compare, snapshot
from feed.sources import ecos, kpx_smp

FIX = Path(__file__).parent / "fixtures"
KPX_HTML = (FIX / "kpx_smp_monthly_20261010.html").read_text(encoding="utf-8")


# --- KPX SMP ---------------------------------------------------------------

def test_kpx_parses_known_values():
    smp = kpx_smp.parse(KPX_HTML)
    mainland = dict(smp["mainland"])
    assert mainland["2026-09"] == 119.02
    assert mainland["2026-08"] == 148.39
    assert mainland["2025-12"] == 90.43
    assert dict(smp["jeju"])["2026-08"] == 149.09


def test_kpx_skips_unpublished_months():
    mainland = dict(kpx_smp.parse(KPX_HTML)["mainland"])
    assert "2026-10" not in mainland
    assert len(mainland) == 12 + 9


def test_kpx_stops_when_a_region_label_changes():
    # A renamed label is not silently treated as data: the row no longer fits the expected shape.
    with pytest.raises(SourceError, match="unexpected row shape"):
        kpx_smp.parse(KPX_HTML.replace("제주 SMP", "제주 계통한계가격"))


def test_kpx_stops_when_a_region_disappears():
    start = KPX_HTML.index('<td rowspan="2">통합 SMP</td>')
    start = KPX_HTML.rindex("<tr>", 0, start)
    end = KPX_HTML.index("</tbody>")
    with pytest.raises(SourceError, match="regions missing"):
        kpx_smp.parse(KPX_HTML[:start] + KPX_HTML[end:])


def test_kpx_stops_when_header_changes():
    with pytest.raises(SourceError, match="header"):
        kpx_smp.parse(KPX_HTML.replace("<th scope=\"col\">12월</th>", ""))


def test_kpx_stops_on_implausible_value():
    with pytest.raises(SourceError, match="implausible"):
        kpx_smp.parse(KPX_HTML.replace("<td>119.02</td>", "<td>11902</td>", 1))


# --- ECOS -------------------------------------------------------------------

def test_ecos_parses_daily_series():
    obs = ecos.parse((FIX / "ecos_ktb3y_20260930.json").read_text(encoding="utf-8"), "817Y002", "010200000", "D")
    assert obs[-1] == ("2026-09-30", 4.011)


def test_ecos_error_response_raises():
    with pytest.raises(SourceError, match="INFO-200"):
        ecos.parse((FIX / "ecos_error.json").read_text(encoding="utf-8"), "999Y999", "010200000", "D")


def test_ecos_rejects_rows_for_another_series():
    payload = (FIX / "ecos_ktb3y_20260930.json").read_text(encoding="utf-8")
    with pytest.raises(SourceError, match="asked"):
        ecos.parse(payload, "817Y002", "010210000", "D")


# --- snapshot ---------------------------------------------------------------

def _fake_sources(monkeypatch, fail_ecos=False):
    monkeypatch.setattr(kpx_smp, "fetch", lambda: kpx_smp.parse(KPX_HTML))

    def fake_ecos(stat, cycle, start, end, item):
        if fail_ecos:
            raise SourceError("ecos down")
        return ([("2026-09-30", 4.0)] if cycle == "D" else [("2026-09", 2.5)]), True

    monkeypatch.setattr(ecos, "fetch", fake_ecos)


def test_snapshot_flags_stale_series(monkeypatch):
    _fake_sources(monkeypatch)
    snap = snapshot.build(today=date(2026, 10, 20))
    assert snap["series"]["ktb_3y"]["stale"] is True          # 20 days > 7
    assert snap["series"]["smp_mainland_monthly"]["stale"] is False


def test_failed_source_writes_nothing(monkeypatch, tmp_path):
    _fake_sources(monkeypatch, fail_ecos=True)
    with pytest.raises(SourceError):
        snapshot.save(snapshot.build(today=date(2026, 10, 10)), tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_diff_reports_revisions():
    prev = {"series": {"s": {"observations": [{"period": "2026-09", "value": 116.74}]}}}
    cur = {"series": {"s": {"observations": [{"period": "2026-09", "value": 119.02},
                                             {"period": "2026-10", "value": 100.0}]}}}
    kinds = {(c["period"], c["kind"]) for c in snapshot.diff(prev, cur)}
    assert kinds == {("2026-09", "revised"), ("2026-10", "new")}


# --- compare ----------------------------------------------------------------

def test_compare_flags_secondary_source_mismatch():
    snap = {"series": {"smp_mainland_monthly": {"observations": [{"period": "2026-08", "value": 148.39}]}}}
    claims = [
        {"series_id": "smp_mainland_monthly", "period": "2026-08", "claimed_value": "148.91", "claimed_source": "blog", "where": "x"},
        {"series_id": "smp_mainland_monthly", "period": "2026-08", "claimed_value": "148.39", "claimed_source": "kpx", "where": "y"},
        {"series_id": "smp_mainland_monthly", "period": "2027-01", "claimed_value": "100", "claimed_source": "?", "where": "z"},
    ]
    status = [r["status"] for r in compare.check(claims, snap)]
    assert status == ["MISMATCH", "MATCH", "NOT_IN_SNAPSHOT"]
