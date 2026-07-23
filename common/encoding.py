"""
Proper HTML decoding. Raw WARC responses can be in any encoding
(Shift-JIS, EUC-JP, Windows-1251, etc). Blindly decoding everything
as UTF-8 with errors="ignore" silently corrupts non-Latin text
instead of failing loudly - this fixes that.

Priority order (most to least reliable):
1. charset declared in the HTTP Content-Type header
2. charset detected from the raw bytes (resiliparse's detector)
3. utf-8 fallback
"""
from typing import Optional


def decode_html(html_bytes: bytes, content_type_header: Optional[str] = None) -> str:
    # 1. Try charset from HTTP header, e.g. "text/html; charset=Shift_JIS"
    if content_type_header and "charset=" in content_type_header.lower():
        charset = content_type_header.lower().split("charset=")[-1].strip().strip('"').strip("'")
        try:
            return html_bytes.decode(charset, errors="strict")
        except (LookupError, UnicodeDecodeError):
            pass  # declared charset was wrong or unsupported - fall through

    # 2. Detect from the bytes themselves
    try:
        from resiliparse.parse.encoding import detect_encoding
        detected = detect_encoding(html_bytes)
        if detected:
            return html_bytes.decode(detected, errors="replace")
    except Exception:
        pass

    # 3. Last resort - utf-8, but "replace" not "ignore" so corruption
    # is visible (U+FFFD) instead of silently vanishing.
    return html_bytes.decode("utf-8", errors="replace")