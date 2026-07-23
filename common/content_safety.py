"""
Content-safety filtering - separate concern from quality filtering.

Quality filters (Stage 3) ask "is this coherent text?"
This asks "do we want this topic in the training set at all?"

Approach mirrors what C4/RefinedWeb-style pipelines do: a domain-level
check (cheapest, catches most cases) plus a keyword-density check on
the text itself (catches cases where the domain name looks innocent).

This is a STARTING LIST, not exhaustive - production pipelines usually
combine this with a maintained blocklist (e.g. UT1) and/or a trained
classifier. Treat this as a first pass, not a complete solution.
"""

# Substrings checked against the URL/domain - cheap, catches most cases
BLOCKED_DOMAIN_KEYWORDS = {
    "porn", "xxx", "sex", "escort", "camgirl", "webcam-", "nude",
    "casino", "bet365", "onlinebetting", "pokerstars",
}

# Word-level keyword list checked against document text.
# Uses a density threshold (not single-hit) so a news article that
# mentions one of these words in passing isn't falsely dropped -
# only text where they dominate the content gets flagged.
BLOCKED_TEXT_KEYWORDS = {
    "porn", "xxx", "escort", "camgirl", "nude", "hardcore",
}
MIN_KEYWORD_HITS_TO_BLOCK = 3


def check_domain(url: str) -> tuple[bool, str | None]:
    url_lower = url.lower()
    for kw in BLOCKED_DOMAIN_KEYWORDS:
        if kw in url_lower:
            return False, f"blocked_domain_keyword:{kw}"
    return True, None


def check_text_keywords(text: str) -> tuple[bool, str | None]:
    text_lower = text.lower()
    words = text_lower.split()
    hits = sum(1 for kw in BLOCKED_TEXT_KEYWORDS if kw in text_lower)
    if hits >= MIN_KEYWORD_HITS_TO_BLOCK:
        return False, f"blocked_keyword_density:{hits}_distinct_terms"
    return True, None


def run_content_safety(url: str, text: str) -> tuple[bool, list[str]]:
    failures = []
    for passed, reason in [check_domain(url), check_text_keywords(text)]:
        if not passed:
            failures.append(reason)
    return len(failures) == 0, failures