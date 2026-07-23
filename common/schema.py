"""
Shared record schema. Every stage reads/writes this shape as JSONL
(one JSON object per line). Keeping one schema stops later stages
from needing fields earlier stages never saved.
"""
from dataclasses import dataclass, asdict, field
from typing import Optional
import json


@dataclass
class Record:
    id: str                     # stable unique id, e.g. warc filename + offset
    url: str
    text: str = ""               # extracted clean text (empty until Stage 1 fills it)
    html_len: int = 0            # length of raw HTML, used by routing.py
    extractor_used: Optional[str] = None   # "trafilatura" | "resiliparse" | None
    lang: Optional[str] = None    # filled in Stage 2 (langid)
    warc_source: str = ""         # which WARC file this came from
    drop_reason: Optional[str] = None  # set by any stage that filters this doc out

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @staticmethod
    def from_json(line: str) -> "Record":
        return Record(**json.loads(line))