"""
Dictionary-grade Japanese pitch accent via pyopenjtalk (OpenJTalk).

OpenJTalk ships an accent dictionary (naist-jdic), so this returns the standard
Tokyo-dialect pitch accent for a word rather than an LLM's guess. Used to
annotate saved notebook vocabulary.

Returns a language-neutral token combining the accent-type name (romaji, so the
frontend can localize it to the interface language) and the drop position (the
"accent nucleus" — the mora after which the pitch falls):

    heiban [0]     — no drop within the word (flat/rising)
    atamadaka [1]  — drops after the first mora
    nakadaka [n]   — drops in the middle
    odaka [N]      — drops after the last mora (before a following particle)
"""

import re

_pyopenjtalk = None


def _engine():
    global _pyopenjtalk
    if _pyopenjtalk is None:
        import pyopenjtalk
        # Apply the same user pronunciation dictionary the TTS uses, so computed
        # pitch accent matches the corrected reading for proper nouns.
        try:
            from jp_userdict import ensure_user_dict_loaded
            ensure_user_dict_loaded()
        except Exception:
            pass
        _pyopenjtalk = pyopenjtalk
    return _pyopenjtalk


def _classify(acc: int, mora: int):
    """Map an accent nucleus position + mora count to a language-neutral token."""
    if mora <= 0 or acc < 0 or acc > mora:
        return None
    if acc == 0:
        return "heiban [0]"
    if acc == 1:
        return "atamadaka [1]"
    if acc >= mora:
        return f"odaka [{acc}]"
    return f"nakadaka [{acc}]"


def _accent_from_fullcontext(pjt, text):
    """(mora_count, accent_nucleus) of the first accent phrase from HTS labels.

    Full-context labels reflect accent sandhi, so this is used for multi-morpheme
    compounds/conjugations where per-morpheme NJD accents don't combine trivially.
    """
    for lab in pjt.extract_fullcontext(text):
        m = re.search(r"/F:(\d+)_(\d+)", lab)
        if m:
            return int(m.group(1)), int(m.group(2))
    return None


def get_pitch_accent(word: str):
    """Return a pitch-accent display string (e.g. '頭高 [1]') for a Japanese word,
    or None if it can't be determined."""
    word = (word or "").strip()
    if not word:
        return None
    try:
        pjt = _engine()
        njd = pjt.run_frontend(word)
        if not njd:
            return None

        if len(njd) == 1:
            # Single dictionary morpheme: NJD carries the exact dictionary accent
            # (correctly distinguishes heiban [0] from odaka [N]).
            mora = int(njd[0].get("mora_size", 0))
            acc = int(njd[0].get("acc", 0))
            return _classify(acc, mora)

        # Compound / conjugation: derive the merged accent phrase from HTS labels.
        fc = _accent_from_fullcontext(pjt, word)
        if not fc:
            return None
        mora, acc = fc
        return _classify(acc, mora)
    except Exception:
        return None
