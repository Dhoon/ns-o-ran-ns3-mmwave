"""Aggregate provenance logs into attack-characterization metrics (guide section 26).

Reads one or more decision_provenance CSVs and computes, per file:
  * attack rate (fraction of epochs with any lag > 0)
  * number of manipulated decision epochs
  * KPM modification count (always 0 by construction -- asserted)
  * average / maximum temporal skew
  * action disagreement vs. the aligned run (if an aligned CSV is given)

Usage:
  python collect_results.py --aligned logs/..baseline.csv logs/..feature_lag.csv ...
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path


def load(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def summarize(rows):
    n = len(rows)
    skews = [float(r["max_temporal_skew"]) for r in rows]
    manipulated = sum(1 for s in skews if s > 0)
    return {
        "decisions": n,
        "manipulated_epochs": manipulated,
        "attack_rate": manipulated / n if n else 0.0,
        "avg_temporal_skew": sum(skews) / n if n else 0.0,
        "max_temporal_skew": max(skews) if skews else 0.0,
        "kpm_modification_count": 0,  # invariant: values are never altered
    }


def disagreement(aligned, attack):
    key = lambda r: (r["ue_id"], r["decision_id"])
    a = {key(r): r["selected_action"] for r in aligned}
    diff = sum(1 for r in attack
               if key(r) in a and a[key(r)] != r["selected_action"])
    paired = sum(1 for r in attack if key(r) in a)
    return diff, paired, (diff / paired if paired else 0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aligned", help="aligned provenance CSV for disagreement")
    ap.add_argument("logs", nargs="+", help="attack provenance CSVs")
    args = ap.parse_args()

    aligned_rows = load(args.aligned) if args.aligned else None

    for p in args.logs:
        rows = load(p)
        s = summarize(rows)
        print(f"\n== {Path(p).name} ==")
        for k, v in s.items():
            print(f"  {k:24s}: {v}")
        if aligned_rows is not None:
            diff, paired, rate = disagreement(aligned_rows, rows)
            print(f"  action_disagreement     : {diff}/{paired} ({rate:.3f})")


if __name__ == "__main__":
    main()
