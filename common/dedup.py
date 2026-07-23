"""
Deduplication - two layers, run in order because exact dedup is
nearly free and shrinks the corpus before the more expensive
near-dup check runs on what's left.

Layer 1 - EXACT dedup: hash the normalized full text. Catches
identical pages (e.g. the same article mirrored/re-crawled).

Layer 2 - NEAR dedup: MinHash + LSH on word shingles. Catches pages
that are almost the same but not byte-identical - e.g. the same
article with a different ad banner, timestamp, or nav menu around it.
This is the standard approach used by CCNet/RefinedWeb-style pipelines
because comparing every doc to every other doc directly (all-pairs)
is O(n^2) and doesn't scale - LSH turns "find near-duplicates" into
an approximate nearest-neighbor lookup instead.
"""
import hashlib
import re
from datasketch import MinHash, MinHashLSH

SHINGLE_SIZE = 5          # number of consecutive words per shingle
NUM_PERM = 128            # MinHash permutations - accuracy/speed tradeoff
NEAR_DUP_THRESHOLD = 0.8  # Jaccard similarity threshold for "near-duplicate"


def normalize_text(text: str) -> str:
    """Lowercase + collapse whitespace, so trivial formatting diffs
    (extra spaces, line breaks) don't defeat exact-dedup hashing."""
    return re.sub(r"\s+", " ", text.lower()).strip()


def exact_hash(text: str) -> str:
    normalized = normalize_text(text)
    return hashlib.blake2b(normalized.encode("utf-8"), digest_size=16).hexdigest()


def get_shingles(text: str, k: int = SHINGLE_SIZE) -> set[str]:
    words = normalize_text(text).split()
    if len(words) < k:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i:i + k]) for i in range(len(words) - k + 1)}


def make_minhash(text: str) -> MinHash:
    m = MinHash(num_perm=NUM_PERM)
    for shingle in get_shingles(text):
        m.update(shingle.encode("utf-8"))
    return m


class Deduplicator:
    """
    Stateful across the whole corpus (not per-file) - duplicates can
    appear in different WARC files, so the seen-hash set and LSH index
    need to persist across every file you process in one run.
    """

    def __init__(self):
        self.seen_exact_hashes: set[str] = set()
        self.lsh = MinHashLSH(threshold=NEAR_DUP_THRESHOLD, num_perm=NUM_PERM)

    def is_duplicate(self, doc_id: str, text: str) -> tuple[bool, str | None]:
        """Returns (is_dup, reason). If not a dup, registers the doc
        (keyed by its own id) so future docs can be checked against it."""
        # Layer 1: exact
        eh = exact_hash(text)
        if eh in self.seen_exact_hashes:
            return True, "exact_duplicate"
        self.seen_exact_hashes.add(eh)

        # Layer 2: near-dup (only reached if not an exact dup)
        mh = make_minhash(text)
        matches = self.lsh.query(mh)
        if matches:
            return True, f"near_duplicate_of:{matches[0]}"

        self.lsh.insert(doc_id, mh)
        return False, None