"""
Stage 2: language filtering

Reads Stage 1's extracted JSONL, detects language per document,
keeps only docs matching --keep-langs, writes survivors onward and
logs everything (kept + dropped) so you can audit decisions later.

Usage:
    python scripts/02_langid.py data/1_extracted/sample_partial.jsonl --keep-langs en
    python scripts/02_langid.py data/1_extracted/sample_partial.jsonl --keep-langs en,fr
"""
import sys
import os
import argparse

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from common.schema import Record
from common.langid_detect import detect_language


def process_file(in_path: str, out_dir: str, keep_langs: set[str]):
    fname = os.path.basename(in_path)
    out_path = os.path.join(out_dir, fname)
    rejected_dir = os.path.join(out_dir, "_rejected")
    os.makedirs(rejected_dir, exist_ok=True)
    rejected_path = os.path.join(rejected_dir, fname)

    n_total, n_kept, n_wrong_lang, n_unknown = 0, 0, 0, 0
    lang_counts: dict[str, int] = {}

    with open(in_path, "r", encoding="utf-8") as in_f, \
         open(out_path, "w", encoding="utf-8") as out_f, \
         open(rejected_path, "w", encoding="utf-8") as rej_f:

        for line in in_f:
            line = line.strip()
            if not line:
                continue
            rec = Record.from_json(line)
            n_total += 1

            # Docs Stage 1 already flagged as bad (e.g. empty extraction) - straight to rejected
            if rec.drop_reason:
                rej_f.write(rec.to_json() + "\n")
                continue

            lang_code, score = detect_language(rec.text)
            rec.lang = lang_code
            lang_counts[lang_code or "unknown"] = lang_counts.get(lang_code or "unknown", 0) + 1

            if lang_code is None:
                n_unknown += 1
                rec.drop_reason = "text_too_short_for_langid"
                rej_f.write(rec.to_json() + "\n")
            elif lang_code not in keep_langs:
                n_wrong_lang += 1
                rec.drop_reason = f"wrong_language:{lang_code}"
                rej_f.write(rec.to_json() + "\n")
            else:
                n_kept += 1
                out_f.write(rec.to_json() + "\n")

    print(f"[{fname}] total: {n_total} | kept: {n_kept} | wrong_lang: {n_wrong_lang} | unknown: {n_unknown}")
    top_langs = sorted(lang_counts.items(), key=lambda x: -x[1])[:10]
    print(f"  language breakdown (top 10): {top_langs}")
    print(f"Survivors written to {out_path}")
    print(f"Rejected (audit log) written to {rejected_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_jsonl", help="Path to Stage 1 output JSONL")
    parser.add_argument("--out-dir", default="data/2_langfiltered")
    parser.add_argument("--keep-langs", default="en", help="Comma-separated language codes to keep, e.g. en,fr")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    keep_langs = set(args.keep_langs.split(","))

    process_file(args.input_jsonl, args.out_dir, keep_langs)