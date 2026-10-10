"""
python -m feed fetch               pull every series, save snapshots/<date>.json, print changes
python -m feed table               print the latest snapshot as a markdown assumption table
python -m feed compare CLAIMS.csv  check quoted numbers against the latest snapshot
"""

import argparse
import sys
from pathlib import Path

from feed import SourceError, compare, snapshot

SNAPSHOTS = Path("snapshots")


def _latest() -> dict:
    paths = sorted(SNAPSHOTS.glob("*.json"))
    if not paths:
        sys.exit("no snapshot yet: run `python -m feed fetch` first")
    return snapshot.load(paths[-1])


def cmd_fetch(_args) -> int:
    try:
        snap = snapshot.build()
    except SourceError as exc:
        print(f"FAILED, nothing written: {exc}", file=sys.stderr)
        return 1
    path = snapshot.save(snap, SNAPSHOTS)
    print(f"saved {path}")

    prev_path = snapshot.latest_before(SNAPSHOTS, snap["as_of"])
    if prev_path:
        for ch in snapshot.diff(snapshot.load(prev_path), snap):
            if ch["kind"] == "revised":
                print(f"  REVISED {ch['series']} {ch['period']}: {ch['from']} -> {ch['value']}")
            else:
                print(f"  new     {ch['series']} {ch['period']}: {ch['value']}")

    stale = [sid for sid, s in snap["series"].items() if s["stale"]]
    for sid in stale:
        s = snap["series"][sid]
        print(f"  STALE   {sid}: latest {s['latest']['period']} is {s['age_days']} days old", file=sys.stderr)
    return 2 if stale else 0


def cmd_table(_args) -> int:
    snap = _latest()
    print(f"As of {snap['as_of']} (retrieved {snap['retrieved_at']})\n")
    print("| Series | Latest | Period | Unit | Source | Grade |")
    print("|---|---|---|---|---|---|")
    for s in snap["series"].values():
        flag = " (stale)" if s["stale"] else ""
        print(f"| {s['label']} | {s['latest']['value']}{flag} | {s['latest']['period']} | {s['unit']} | {s['source_url']} | {s['grade']} |")
    return 0


def cmd_compare(args) -> int:
    snap = _latest()
    results = compare.check(compare.load_claims(Path(args.claims)), snap)
    print(f"Checked against snapshot {snap['as_of']}\n")
    print("| Where | Series | Period | Claimed | Claimed source | Primary | Delta | Status |")
    print("|---|---|---|---|---|---|---|---|")
    for r in results:
        print(f"| {r['where']} | {r['series_id']} | {r['period']} | {r['claimed_value']} | {r['claimed_source']} "
              f"| {r['primary_value']} | {r['delta']} | {r['status']} |")
    return 0 if all(r["status"] == "MATCH" for r in results) else 3


def main() -> int:
    parser = argparse.ArgumentParser(prog="feed")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch").set_defaults(func=cmd_fetch)
    sub.add_parser("table").set_defaults(func=cmd_table)
    p = sub.add_parser("compare")
    p.add_argument("claims")
    p.set_defaults(func=cmd_compare)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
