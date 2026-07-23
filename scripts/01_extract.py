"""
Stage 1: WARC -> extracted text (JSONL)

WARC = "Web ARChive" format. It's basically a container of raw HTTP
responses Common Crawl saved while crawling - full HTML + headers,
one record per page fetched.

Usage:
    python scripts/01_extract.py path/to/file.warc.gz
"""
import sys
import os
import hashlib
from warcio.archiveiterator import ArchiveIterator

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from common.schema import Record
from common.routing import extract_text
from common.encoding import decode_html


def make_id(warc_source: str, warc_record_id: str) -> str:
    raw = f"{warc_source}:{warc_record_id}"
    return hashlib.blake2b(raw.encode(), digest_size=8).hexdigest()


def process_warc(warc_path: str, out_path: str):
    warc_name = os.path.basename(warc_path)
    n_seen, n_written, n_empty = 0, 0, 0

    with open(warc_path, "rb") as stream, open(out_path, "w", encoding="utf-8") as out_f:
        for record in ArchiveIterator(stream):
            # WARC files contain several record types (request, metadata,
            # response...). We only want actual page responses.
            if record.rec_type != "response":
                continue

            content_type = record.http_headers.get_header("Content-Type", "") if record.http_headers else ""
            if "html" not in (content_type or ""):
                continue

            n_seen += 1
            url = record.rec_headers.get_header("WARC-Target-URI") or ""

            try:
                html_bytes = record.content_stream().read()
                html = decode_html(html_bytes, content_type)
            except Exception:
                continue

            if not html.strip():
                continue

            text, extractor_used = extract_text(html, url)

            warc_record_id = record.rec_headers.get_header("WARC-Record-ID") or url
            rec = Record(
                id=make_id(warc_name, warc_record_id),
                url=url,
                text=text,
                html_len=len(html),
                extractor_used=extractor_used,
                warc_source=warc_name,
            )

            if not text.strip():
                n_empty += 1
                rec.drop_reason = "empty_extraction"
            else:
                n_written += 1

            out_f.write(rec.to_json() + "\n")

    print(f"[{warc_name}] pages seen: {n_seen} | extracted: {n_written} | empty: {n_empty}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python 01_extract.py <path_to.warc.gz> [output_dir]")
        sys.exit(1)

    warc_path = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "data/1_extracted"
    os.makedirs(out_dir, exist_ok=True)

    out_name = os.path.basename(warc_path).replace(".warc.gz", "").replace(".warc", "") + ".jsonl"
    out_path = os.path.join(out_dir, out_name)

    process_warc(warc_path, out_path)
    print(f"Written to {out_path}")