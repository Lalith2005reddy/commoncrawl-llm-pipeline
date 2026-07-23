"""
Routing decides, per page, whether to use trafilatura or resiliparse.

Why route at all instead of always using one?
- trafilatura: better at picking out the "real" article text on
  content-heavy pages (news, blogs, docs). Slower.
- resiliparse: much faster, C++ backed. Better choice for very large
  pages or simple/short pages where trafilatura's extra analysis
  doesn't buy you anything.

The heuristic below is simple on purpose - a starting point, not
a final answer. Signal 1 (html size) is the cheapest and most useful.
"""

# Tune these after you see real data - these are reasonable starting points
LARGE_HTML_BYTES = 300_000   # ~300KB: big pages -> favor speed (resiliparse)
SMALL_HTML_BYTES = 2_000     # tiny pages -> not worth trafilatura's overhead


def choose_extractor(html: str, url: str = "") -> str:
    """Returns 'trafilatura' or 'resiliparse' for a given raw HTML string."""
    size = len(html)

    if size > LARGE_HTML_BYTES:
        return "resiliparse"       # big page: prioritize speed
    if size < SMALL_HTML_BYTES:
        return "resiliparse"       # tiny page: trafilatura's analysis is overkill

    # mid-sized pages: default to trafilatura for higher extraction quality
    return "trafilatura"


def extract_text(html: str, url: str = "") -> tuple[str, str]:
    """
    Runs the chosen extractor. Returns (text, extractor_name_used).
    Falls back to the other extractor if the first returns nothing -
    some pages trip up one extractor but not the other.
    """
    choice = choose_extractor(html, url)

    text = _run_trafilatura(html) if choice == "trafilatura" else _run_resiliparse(html)

    if not text or not text.strip():
        # fallback: try the other one before giving up
        fallback = "resiliparse" if choice == "trafilatura" else "trafilatura"
        text = _run_resiliparse(html) if fallback == "resiliparse" else _run_trafilatura(html)
        choice = fallback if text and text.strip() else choice

    return text or "", choice


def _run_trafilatura(html: str) -> str:
    import trafilatura
    result = trafilatura.extract(html, include_comments=False, include_tables=False)
    return result or ""


def _run_resiliparse(html: str) -> str:
    from resiliparse.extract.html2text import extract_plain_text
    from resiliparse.parse.encoding import detect_encoding
    try:
        return extract_plain_text(html) or ""
    except Exception:
        return ""