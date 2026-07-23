"""
Stage 3: quality filtering

Reads Stage 2's language-filtered JSONL, runs Gopher-style heuristic
rules, keeps only docs that pass everything, writes survivors onward
plus a rejected audit log with per-doc failure reasons.

Usage:
    python scripts/03_quality_filter.py data/2_langfiltered/sample_partial.jsonl
"""
import sys
import os
import argparse
from collections import Counter

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from common.schema import Record
from common.quality_filters import run_quality_filters


def process_file(in_path: str, out_dir: str):
    fname = os.path.basename(in_path)
    out_path = os.path.join(out_dir, fname)
    rejected_dir = os.path.join(out_dir, "_rejected")
    os.makedirs(rejected_dir, exist_ok=True)
    rejected_path = os.path.join(rejected_dir, fname)

    n_total, n_kept, n_dropped = 0, 0, 0
    reason_counts: Counter = Counter()

    with open(in_path, "r", encoding="utf-8") as in_f, \
         open(out_path, "w", encoding="utf-8") as out_f, \
         open(rejected_path, "w", encoding="utf-8") as rej_f:

        for line in in_f:
            line = line.strip()
            if not line:
                continue
            rec = Record.from_json(line)
            n_total += 1

            passed, failures = run_quality_filters(rec.text)

            if passed:
                n_kept += 1
                out_f.write(rec.to_json() + "\n")
            else:
                n_dropped += 1
                rec.drop_reason = "quality:" + ",".join(failures)
                for f in failures:
                    reason_counts[f.split(":")[0]] += 1
                rej_f.write(rec.to_json() + "\n")

    print(f"[{fname}] total: {n_total} | kept: {n_kept} | dropped: {n_dropped}")
    print(f"  drop reasons (rule -> count): {reason_counts.most_common()}")
    print(f"Survivors written to {out_path}")
    print(f"Rejected (audit log) written to {rejected_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_jsonl", help="Path to Stage 2 output JSONL")
    parser.add_argument("--out-dir", default="data/3_quality_filtered")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    process_file(args.input_jsonl, args.out_dir)