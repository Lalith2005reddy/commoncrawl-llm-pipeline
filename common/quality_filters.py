"""
Quality filters - heuristic rules to drop low-quality text before
it reaches training data. Based on the "Gopher rules" approach
(DeepMind's Gopher paper) - simple, fast, explainable checks rather
than a learned quality classifier.

Each rule is a standalone function: (text) -> (passed: bool, reason: str|None)
This is deliberate - keeping rules independent means:
  - you can log exactly which rule killed a doc
  - you can add/remove/retune one rule without touching the others
  - you can measure how many docs each rule alone would drop
"""
import re

# ---- tunable thresholds - adjust after looking at real data ----
MIN_WORDS = 50
MAX_WORDS = 100_000
MIN_MEAN_WORD_LEN = 3      # too low -> garbled/spam text
MAX_MEAN_WORD_LEN = 10     # too high -> not natural language (e.g. URLs, code)
MAX_SYMBOL_TO_WORD_RATIO = 0.1
MIN_ALPHA_RATIO = 0.6      # fraction of characters that are alphabetic
MAX_REPEATED_LINE_FRACTION = 0.3

ENGLISH_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
    "in", "on", "at", "to", "of", "for", "with", "this", "that", "it",
}
MIN_STOPWORD_COUNT = 2  # real prose has stopwords; keyword-stuffed spam often doesn't

LOREM_IPSUM_MARKER = "lorem ipsum"


def check_word_count(text: str) -> tuple[bool, str | None]:
    n_words = len(text.split())
    if n_words < MIN_WORDS:
        return False, f"too_few_words:{n_words}"
    if n_words > MAX_WORDS:
        return False, f"too_many_words:{n_words}"
    return True, None


def check_mean_word_length(text: str) -> tuple[bool, str | None]:
    words = text.split()
    if not words:
        return False, "no_words"
    mean_len = sum(len(w) for w in words) / len(words)
    if mean_len < MIN_MEAN_WORD_LEN:
        return False, f"mean_word_len_too_low:{mean_len:.1f}"
    if mean_len > MAX_MEAN_WORD_LEN:
        return False, f"mean_word_len_too_high:{mean_len:.1f}"
    return True, None


def check_symbol_ratio(text: str) -> tuple[bool, str | None]:
    words = text.split()
    if not words:
        return False, "no_words"
    symbol_words = sum(1 for w in words if not any(c.isalnum() for c in w))
    ratio = symbol_words / len(words)
    if ratio > MAX_SYMBOL_TO_WORD_RATIO:
        return False, f"too_many_symbol_words:{ratio:.2f}"
    return True, None


def check_alpha_ratio(text: str) -> tuple[bool, str | None]:
    if not text:
        return False, "empty_text"
    alpha_chars = sum(1 for c in text if c.isalpha())
    ratio = alpha_chars / len(text)
    if ratio < MIN_ALPHA_RATIO:
        return False, f"alpha_ratio_too_low:{ratio:.2f}"
    return True, None


def check_repeated_lines(text: str) -> tuple[bool, str | None]:
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if len(lines) < 5:
        return True, None  # too few lines for this check to be meaningful
    unique_lines = len(set(lines))
    repeated_fraction = 1 - (unique_lines / len(lines))
    if repeated_fraction > MAX_REPEATED_LINE_FRACTION:
        return False, f"too_many_repeated_lines:{repeated_fraction:.2f}"
    return True, None


def check_stopwords(text: str) -> tuple[bool, str | None]:
    words = set(w.lower().strip(".,!?;:\"'") for w in text.split())
    stopword_hits = len(words & ENGLISH_STOPWORDS)
    if stopword_hits < MIN_STOPWORD_COUNT:
        return False, f"too_few_stopwords:{stopword_hits}"
    return True, None


def check_lorem_ipsum(text: str) -> tuple[bool, str | None]:
    if LOREM_IPSUM_MARKER in text.lower():
        return False, "lorem_ipsum_placeholder"
    return True, None


# Order matters a little for readability of logs, not for correctness -
# every rule runs regardless of earlier results.
ALL_RULES = [
    check_word_count,
    check_mean_word_length,
    check_symbol_ratio,
    check_alpha_ratio,
    check_repeated_lines,
    check_stopwords,
    check_lorem_ipsum,
]


def run_quality_filters(text: str) -> tuple[bool, list[str]]:
    """
    Runs all rules. Returns (passed_all, list_of_failure_reasons).
    passed_all is True only if every rule passed.
    """
    failures = []
    for rule in ALL_RULES:
        passed, reason = rule(text)
        if not passed:
            failures.append(reason)
    return len(failures) == 0, failures