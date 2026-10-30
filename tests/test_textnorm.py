import re

from kavach.textnorm import is_negated, normalize


def test_normalize_composes_unicode_and_casefolds():
    assert normalize("Café CBI") == "café cbi"


def test_normalize_strips_abbreviation_dots_latin_and_devanagari():
    assert normalize("C.B.I. officer") == "cbi. officer"
    assert normalize("सी.बी.आई. अधिकारी") == "सीबीआई. अधिकारी"


def test_normalize_collapses_whitespace():
    assert normalize("  police \n  wale  ") == "police wale"


def _neg(text: str, phrase: str) -> bool:
    t = normalize(text)
    m = re.search(re.escape(phrase), t)
    assert m, f"{phrase!r} not in {t!r}"
    return is_negated(t, m.start(), m.end())


def test_negation_before_match_suppresses():
    assert _neg("No, nobody from police called", "police")


def test_clause_boundary_stops_negation():
    assert not _neg("No, the CBI officer called me", "cbi officer")


def test_negation_inside_match_does_not_suppress():
    assert not _neg("They said don't tell anyone", "don't tell anyone")


def test_contraction_negates():
    assert _neg("They didn't say I will be arrested", "will be arrested")


def test_hindi_negator_after_match_suppresses():
    assert _neg("पुलिस वाले ने फोन नहीं किया", "पुलिस वाले")


def test_conditional_to_resets_window():
    assert not _neg("पैसे नहीं भेजे तो गिरफ्तार कर लेंगे", "गिरफ्तार")
