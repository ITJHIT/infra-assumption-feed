"""The series this tool knows how to pull. Item codes were checked against live ECOS responses."""

KPX_SMP = [
    {"id": "smp_mainland_monthly", "label": "SMP, mainland, monthly average", "region": "mainland"},
    {"id": "smp_jeju_monthly", "label": "SMP, Jeju, monthly average", "region": "jeju"},
]
for s in KPX_SMP:
    s.update(source="kpx_smp", unit="KRW/kWh", cycle="M", max_age_days=45)

ECOS = [
    {"id": "bok_base_rate", "label": "Bank of Korea base rate", "stat": "722Y001", "item": "0101000", "cycle": "M", "max_age_days": 45},
    {"id": "ktb_3y", "label": "Korea Treasury Bond 3Y yield", "stat": "817Y002", "item": "010200000", "cycle": "D", "max_age_days": 7},
    {"id": "ktb_5y", "label": "Korea Treasury Bond 5Y yield", "stat": "817Y002", "item": "010200001", "cycle": "D", "max_age_days": 7},
    {"id": "ktb_10y", "label": "Korea Treasury Bond 10Y yield", "stat": "817Y002", "item": "010210000", "cycle": "D", "max_age_days": 7},
    {"id": "corp_aa_minus_3y", "label": "Corporate bond 3Y (AA-) yield", "stat": "817Y002", "item": "010300000", "cycle": "D", "max_age_days": 7},
]
for s in ECOS:
    s.update(source="ecos", unit="% p.a.")

SERIES = KPX_SMP + ECOS
BY_ID = {s["id"]: s for s in SERIES}
