# commoncrawl-llm-pipeline

Production-style data pipeline that extracts, filters, deduplicates, and shards Common Crawl WARC data into clean text ready for LLM pretraining.

## Status: v1 complete

All stages implemented and tested end-to-end on a real Common Crawl WARC sample:

```
1344 raw pages
  -> 362  passed language filter (English)
  -> 227  passed quality filter
  -> 220  passed content-safety filter
  -> 212  passed deduplication
  -> 212  final docs, sharded for training
```

## Pipeline stages

```
data/
  0_raw_warc/            raw WARC files (input, not committed)
  1_extracted/            extracted text, JSONL (Stage 1)
  2_langfiltered/          language-filtered, JSONL (Stage 2)
    _rejected/              docs dropped here, with reasons
  3_quality_filtered/      quality-filtered, JSONL (Stage 3)
    _rejected/
  3b_safety_filtered/      content-safety-filtered, JSONL (Stage 3b)
    _rejected/
  4_deduped/               deduplicated, JSONL (Stage 4)
    _rejected/
  5_final_shards/          final training-ready shards (Stage 5)
```

Every `_rejected/` folder is an audit log - each dropped doc keeps its original fields plus a `drop_reason` explaining exactly why it didn't make it through. Nothing is silently discarded.

1. **Extraction** (`scripts/01_extract.py`) - reads raw WARC files, routes each page to `trafilatura` or `resiliparse` based on page size, extracts clean text. Handles per-page character encoding detection (not a blind UTF-8 assumption).
2. **Language ID** (`scripts/02_langid.py`) - filters to target language(s) using `py3langid`.
3. **Quality filtering** (`scripts/03_quality_filter.py`) - Gopher-style heuristic rules: word count bounds, mean word length, symbol ratio, alphabetic ratio, repeated-line ratio, stopword presence, lorem-ipsum detection.
4. **Content-safety filtering** (`scripts/03b_content_safety.py`) - domain and keyword-density based filtering. Starting list, not exhaustive - see file docstring.
5. **Deduplication** (`scripts/04_dedup.py`) - exact hash dedup + MinHash/LSH near-duplicate detection (catches re-published/syndicated content with different boilerplate).
6. **Shard output** (`scripts/05_shard_output.py`) - fixed-size JSONL shards.

Plus `scripts/pipeline_report.py` - reconstructs the full funnel (doc counts at every stage) by reading what's already on disk, no re-run needed.

## Record schema

Every stage reads/writes the same JSONL record shape, defined in `common/schema.py`:

```json
{"id": "...", "url": "...", "text": "...", "html_len": 0, "extractor_used": null, "lang": null, "warc_source": "...", "drop_reason": null}
```

## Setup

```bash
pip install warcio trafilatura resiliparse py3langid datasketch
```

## Usage

```bash
# Stage 1: extraction
python scripts/01_extract.py data/0_raw_warc/sample.warc.gz

# Stage 2: language filtering
python scripts/02_langid.py data/1_extracted/sample.jsonl --keep-langs en

# Stage 3: quality filtering
python scripts/03_quality_filter.py data/2_langfiltered/sample.jsonl

# Stage 3b: content-safety filtering
python scripts/03b_content_safety.py data/3_quality_filtered/sample.jsonl

# Stage 4: deduplication (pass all files in one run to dedup across them)
python scripts/04_dedup.py data/3b_safety_filtered/sample.jsonl

# Stage 5: shard output
python scripts/05_shard_output.py data/4_deduped --shard-size 10000

# Full pipeline funnel report
python scripts/pipeline_report.py
```

## Known limitations / next steps

- Thresholds (quality filter cutoffs, content-safety keyword lists, dedup similarity threshold) are hardcoded starting points in `common/*.py`, not yet in a config file.
- Content-safety keyword/domain lists are a starting point, not a maintained blocklist - not comprehensive.
- Tested at small scale (single WARC file, partial download). Not yet run against a full-size crawl segment or multiple files in parallel.
- No automated test suite yet - testing has been manual, stage by stage.