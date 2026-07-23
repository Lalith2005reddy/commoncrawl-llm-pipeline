"""
Pipeline funnel report - shows doc counts at every stage by counting
lines in each stage's output files on disk. Doesn't re-run anything,
just reads what's already there. This is the "did the whole pipeline
actually do something sensible end to end" sanity check.

Usage:
    python scripts/pipeline_report.py
"""
import os
import glob


def count_lines(path_pattern: str) -> int:
    total = 0
    for path in glob.glob(path_pattern):
        with open(path, "r", encoding="utf-8") as f:
            total += sum(1 for line in f if line.strip())
    return total


STAGES = [
    ("Stage 1 - extracted (all)",        "data/1_extracted/*.jsonl"),
    ("Stage 2 - lang survivors",         "data/2_langfiltered/*.jsonl"),
    ("Stage 2 - lang rejected",          "data/2_langfiltered/_rejected/*.jsonl"),
    ("Stage 3 - quality survivors",      "data/3_quality_filtered/*.jsonl"),
    ("Stage 3 - quality rejected",       "data/3_quality_filtered/_rejected/*.jsonl"),
    ("Stage 3b - safety survivors",      "data/3b_safety_filtered/*.jsonl"),
    ("Stage 3b - safety rejected",       "data/3b_safety_filtered/_rejected/*.jsonl"),
    ("Stage 4 - dedup survivors",        "data/4_deduped/*.jsonl"),
    ("Stage 4 - dedup rejected",         "data/4_deduped/_rejected/*.jsonl"),
    ("Stage 5 - final shards",           "data/5_final_shards/*.jsonl"),
]

if __name__ == "__main__":
    print(f"{'Stage':<35} {'Doc count':>10}")
    print("-" * 47)
    raw_total = None
    for label, pattern in STAGES:
        n = count_lines(pattern)
        print(f"{label:<35} {n:>10}")
        if label.startswith("Stage 1"):
            raw_total = n

    final_n = count_lines("data/5_final_shards/*.jsonl")
    if raw_total:
        pct = 100 * final_n / raw_total
        print("-" * 47)
        print(f"Overall retention: {final_n}/{raw_total} = {pct:.1f}% of extracted pages made it to final training data")