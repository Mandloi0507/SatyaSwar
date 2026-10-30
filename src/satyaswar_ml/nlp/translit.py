"""
Devanagari to Latin transliteration and phonetic key normalisation.
Authoritative source: Implementation.md, Section 7.9
"""

from __future__ import annotations

import re

from indic_transliteration import sanscript

HONORIFICS = {"ji", "sir", "madam", "bhai", "didi", "uncle", "aunty", "sahab", "saheb"}


def is_devanagari(text: str) -> bool:
    """Check if string contains Devanagari Unicode characters (U+0900 to U+097F)."""
    return any("\u0900" <= ch <= "\u097f" for ch in text)


def transliterate_to_latin(text: str) -> str:
    """Transliterate Devanagari text to Latin using ITRANS scheme."""
    if is_devanagari(text):
        return sanscript.transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
    return text


def phonetic_key(text: str) -> str:
    """
    Produce normalized phonetic key for robust Indian name and keyword matching.
    Steps:
      1. Transliterate Devanagari to Latin if needed.
      2. Lowercase and remove punctuation.
      3. Strip honorifics (ji, sir, bhai, didi, etc.).
      4. Collapse phonetic spelling variants:
         - aa -> a, ee/ii -> i, oo/uu -> u
         - w -> v, z -> j, ph -> f
         - aspirated stops to plain: th->t, dh->d, kh->k, gh->g, bh->b, ch->c, jh->j, sh->s
         - collapse doubled letters: ll -> l, mm -> m, etc.
         - drop trailing schwa 'a'
    """
    if not text:
        return ""

    # 1. Transliterate Devanagari
    latin = transliterate_to_latin(text)

    # 2. Lowercase & strip punctuation
    cleaned = re.sub(r"[^\w\s]", " ", latin.lower())

    # 3. Strip honorifics
    tokens = [t for t in cleaned.split() if t and t not in HONORIFICS]
    if not tokens:
        return ""

    joined = " ".join(tokens)

    # 4. Collapse phonetic spelling variants
    s = joined
    # Vowels
    s = re.sub(r"aa+", "a", s)
    s = re.sub(r"ee+|ii+", "i", s)
    s = re.sub(r"oo+|uu+", "u", s)
    # Consonants
    s = s.replace("w", "v")
    s = s.replace("z", "j")
    s = s.replace("ph", "f")
    # Aspirated stops to plain
    s = s.replace("th", "t")
    s = s.replace("dh", "d")
    s = s.replace("kh", "k")
    s = s.replace("gh", "g")
    s = s.replace("bh", "b")
    s = s.replace("sh", "s")
    s = s.replace("jh", "j")
    s = s.replace("ch", "c")

    # Collapse adjacent duplicate characters (e.g. shuklaa -> shukla, priyanka -> priyanka)
    s = re.sub(r"([a-z])\1+", r"\1", s)

    # Drop trailing schwa 'a' on words of length > 3 (e.g. priyanka -> priyank, abhishek -> abhishek)
    words = []
    for w in s.split():
        if len(w) > 3 and w.endswith("a"):
            w = w[:-1]
        words.append(w)

    return " ".join(words)
