"""
Language detection wrapper around py3langid.

Why wrap it instead of calling py3langid directly in the stage script:
- keeps a min-length guard in one place (langid is unreliable on very
  short text - it'll happily call an empty string "English")
- gives you one place to swap in a different detector later (e.g.
  fastText's lid.176 model) without touching the stage script
"""
import py3langid as langid

MIN_CHARS_FOR_DETECTION = 20


def detect_language(text: str) -> tuple[str | None, float | None]:
    """
    Returns (lang_code, score) or (None, None) if text is too short
    to reliably detect. lang_code is None -> caller should treat this
    doc as "unknown", not confidently drop or keep it based on language.
    """
    if not text or len(text.strip()) < MIN_CHARS_FOR_DETECTION:
        return None, None

    lang_code, score = langid.classify(text)
    return lang_code, float(score)