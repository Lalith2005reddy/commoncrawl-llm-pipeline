# commoncrawl-llm-pipeline

Production-style data pipeline that extracts, filters, deduplicates, and shards Common Crawl WARC data into clean text ready for LLM pretraining.

## Pipeline stages

```
data/
  0_raw_warc/          raw WARC files (input, not committed)
  1_extracted/          extracted text, JSONL (Stage 1)
  2_langfiltered/        language-filtered, JSONL (Stage 2)
  3_quality_filtered/    quality-filtered, JSONL (Stage 3)
  4_deduped/             deduplicated, JSONL (Stage 4)
  5_final_shards/        final training-ready shards (Stage 5)
```

1. **Extraction** (`scripts/01_extract.py`) - reads raw WARC files, routes each page to `trafilatura` or `resiliparse` based on page size, extracts clean text.
2. **Language ID** *(planned)* - filters to target language(s) using fastText.
3. **Quality filtering** *(planned)* - Gopher-style heuristic rules (length bounds, symbol ratio, repeated lines).
4. **Deduplication** *(planned)* - exact hash dedup + MinHash/LSH near-dedup.
5. **Shard output** *(planned)* - fixed-size JSONL shards ready for tokenization.

## Record schema

Every stage reads/writes the same JSONL record shape, defined in `common/schema.py`:

```json
{"id": "...", "url": "...", "text": "...", "html_len": 0, "extractor_used": null, "lang": null, "warc_source": "...", "drop_reason": null}
```

## Setup

```bash
pip install warcio trafilatura resiliparse
```

## Usage

```bash
python scripts/01_extract.py path/to/file.warc.gz
```

Writes extracted JSONL to `data/1_extracted/`.

## Status

Stage 1 (extraction) working. Stages 2-5 in progress.