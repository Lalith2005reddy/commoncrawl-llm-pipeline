"""
Stage 4: deduplication

Reads Stage 3b's content-safety-filtered JSONL, drops exact and
near-duplicates, writes survivors onward plus a rejected audit log.

Note: dedup state (seen hashes + LSH index) is per RUN, not per file -
if you process multiple files, pass them all in one run so duplicates
across files get caught too (that's what --input accepting multiple
paths is for).

Usage:
    python scripts/04_dedup.py data/3b_safety_filtered/sample_partial.jsonl
    python scripts/04_dedup.py data/3b_safety_filtered/*.jsonl
"""
import sys
import os
import argparse
from collections import Counter

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from common.schema import Record
from common.dedup import Deduplicator


def process_files(in_paths: list[str], out_dir: str):
    rejected_dir = os.path.join(out_dir, "_rejected")
    os.makedirs(rejected_dir, exist_ok=True)

    dedup = Deduplicator()  # shared across all files in this run
    n_total, n_kept, n_exact, n_near = 0, 0, 0, 0
    reason_counts: Counter = Counter()

    for in_path in in_paths:
        fname = os.path.basename(in_path)
        out_path = os.path.join(out_dir, fname)
        rejected_path = os.path.join(rejected_dir, fname)

        with open(in_path, "r", encoding="utf-8") as in_f, \
             open(out_path, "w", encoding="utf-8") as out_f, \
             open(rejected_path, "w", encoding="utf-8") as rej_f:

            for line in in_f:
                line = line.strip()
                if not line:
                    continue
                rec = Record.from_json(line)
                n_total += 1

                is_dup, reason = dedup.is_duplicate(rec.id, rec.text)

                if is_dup:
                    if reason == "exact_duplicate":
                        n_exact += 1
                    else:
                        n_near += 1
                    reason_counts[reason.split(":")[0]] += 1
                    rec.drop_reason = f"dedup:{reason}"
                    rej_f.write(rec.to_json() + "\n")
                else:
                    n_kept += 1
                    out_f.write(rec.to_json() + "\n")

        print(f"[{fname}] processed")

    print(f"\nTotal: {n_total} | kept: {n_kept} | exact_dups: {n_exact} | near_dups: {n_near}")
    print(f"  reasons: {reason_counts.most_common()}")
    print(f"Survivors written to {out_dir}/")
    print(f"Rejected (audit log) written to {rejected_dir}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_jsonl", nargs="+", help="Path(s) to Stage 3b output JSONL - pass all files in one run to dedup across them")
    parser.add_argument("--out-dir", default="data/4_deduped")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    process_files(args.input_jsonl, args.out_dir)