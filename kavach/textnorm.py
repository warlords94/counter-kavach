import re
import unicodedata

NUKTA = "़"
_ABBR_DOT = re.compile(r"(?<=[a-zऀ-ॣ])\.(?=[a-zऀ-ॣ])")
_WS = re.compile(r"\s+")
_TOKEN = re.compile(r"[a-z0-9'ऀ-ॣ०-ॿ]+")
_CLAUSE_BREAK = re.compile(r"[.!?।॥,;:\n]")

NEGATORS_BEFORE = {
    "no", "not", "nobody", "never", "none", "nothing", "nahi", "nahin", "nhi", "mat",
    "dont", "didnt", "doesnt", "cant", "wont", "wasnt", "werent", "isnt", "havent", "hasnt",
    "नहीं", "नही", "मत",
}
NEGATORS_AFTER = {"nahi", "nahin", "nhi", "नहीं", "नही"}
# Words that start a new clause for negation purposes ("if you don't pay, THEN arrest").
CLAUSE_WORDS = {"तो", "वरना", "लेकिन", "मगर", "warna", "lekin", "magar", "but", "then", "otherwise", "else"}


def fold(text: str) -> str:
    """NFC and drop the nukta, so typed and transcribed Devanagari compare equal. Safe for regex patterns."""
    return unicodedata.normalize("NFC", text).replace(NUKTA, "")


def normalize(text: str) -> str:
    s = fold(text).replace("’", "'").casefold()
    s = _ABBR_DOT.sub("", s)
    return _WS.sub(" ", s).strip()


def _is_negator(token: str) -> bool:
    return token in NEGATORS_BEFORE or token.endswith("n't")


def is_negated(text: str, start: int, end: int, rules_cfg: dict | None = None) -> bool:
    """True if a negation cue governs text[start:end]; text must already be normalized."""
    n_before = (rules_cfg or {}).get("negation_window_before", 4)
    n_after = (rules_cfg or {}).get("negation_window_after", 3)

    before = text[:start]
    breaks = list(_CLAUSE_BREAK.finditer(before))
    if breaks:
        before = before[breaks[-1].end():]
    tokens = _TOKEN.findall(before)
    for i in range(len(tokens) - 1, -1, -1):
        if tokens[i] in CLAUSE_WORDS:
            tokens = tokens[i + 1:]
            break
    if any(_is_negator(t) for t in tokens[-n_before:]):
        return True

    after = text[end:]
    brk = _CLAUSE_BREAK.search(after)
    if brk:
        after = after[:brk.start()]
    return any(t in NEGATORS_AFTER for t in _TOKEN.findall(after)[:n_after])
