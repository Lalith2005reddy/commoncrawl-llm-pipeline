# commoncrawl-llm-pipeline
Production-style data pipeline that extracts, filters, deduplicates, and shards Common Crawl WARC data into clean text ready for LLM pretraining. Hybrid extraction routing (trafilatura + resiliparse), quality filtering, and MinHash-based near-dedup.
