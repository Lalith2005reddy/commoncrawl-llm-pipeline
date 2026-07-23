"""
Stage 5: shard output

Reads Stage 4's deduped JSONL (all files), combines everything, and
writes fixed-size shards ready for tokenization. Sharding into equal
chunks (rather than one giant file) matters for real training
pipelines - it lets you parallelize tokenization/loading and shuffle
at the shard level without loading the whole dataset into memory.

Usage:
    python scripts/05_shard_output.py data/4_deduped
"""
import sys
import os
import glob
import argparse

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from common.schema import Record

DEFAULT_SHARD_SIZE = 1000  # docs per shard - tune up for real runs


def gather_input_files(in_dir: str) -> list[str]:
    # Only top-level jsonl files, not the _rejected subfolder
    return sorted(glob.glob(os.path.join(in_dir, "*.jsonl")))


def write_shards(in_dir: str, out_dir: str, shard_size: int):
    input_files = gather_input_files(in_dir)
    if not input_files:
        print(f"No input files found in {in_dir}")
        return

    shard_idx = 0
    buffer = []
    n_total = 0

    def flush_shard():
        nonlocal shard_idx, buffer
        if not buffer:
            return
        shard_path = os.path.join(out_dir, f"shard_{shard_idx:05d}.jsonl")
        with open(shard_path, "w", encoding="utf-8") as f:
            for rec in buffer:
                f.write(rec.to_json() + "\n")
        print(f"  wrote {shard_path} ({len(buffer)} docs)")
        shard_idx += 1
        buffer = []

    for in_path in input_files:
        with open(in_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = Record.from_json(line)
                buffer.append(rec)
                n_total += 1
                if len(buffer) >= shard_size:
                    flush_shard()

    flush_shard()  # final partial shard
    print(f"\nTotal docs sharded: {n_total} across {shard_idx} shard(s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir", help="Directory of Stage 4 output JSONL files (e.g. data/4_deduped)")
    parser.add_argument("--out-dir", default="data/5_final_shards")
    parser.add_argument("--shard-size", type=int, default=DEFAULT_SHARD_SIZE)
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    write_shards(args.input_dir, args.out_dir, args.shard_size)