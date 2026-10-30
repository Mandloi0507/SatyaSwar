"""
Context scam keyword spotting and category rule matcher.
Authoritative source: Implementation.md, Section 7.8, Appendix B
"""

from __future__ import annotations

from pathlib import Path

import yaml
from rapidfuzz import fuzz

from satyaswar_ml.nlp.translit import phonetic_key
from satyaswar_ml.schemas import ContextCategoryType, ContextFlag


class KeywordMatcher:
    """
    Spot scam keywords in transcript across English, Hinglish, and Devanagari.
    Normalizes transcript and keywords using phonetic keys.
    """

    def __init__(self, keywords_path: str | Path | None = None):
        if not keywords_path:
            keywords_path = Path(__file__).parent.parent.parent.parent / "configs" / "keywords.yaml"
            if not keywords_path.is_file():
                keywords_path = Path("configs/keywords.yaml")

        self.lexicon: dict[ContextCategoryType, dict[str, list[str]]] = {}
        if Path(keywords_path).is_file():
            with open(keywords_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    self.lexicon = loaded

        # Precompute normalized phonetic keys for all lexicon terms
        # Map: category -> list of (raw_term, lang_key, normalized_key, is_short)
        self.indexed_terms: list[tuple[ContextCategoryType, str, str, str, bool]] = []
        for cat, lang_dict in self.lexicon.items():
            if not isinstance(lang_dict, dict):
                continue
            for lang, terms in lang_dict.items():
                if not isinstance(terms, list):
                    continue
                for term in terms:
                    norm = phonetic_key(str(term))
                    if norm:
                        is_short = len(norm) < 4
                        self.indexed_terms.append((cat, str(term), lang, norm, is_short))

    def scan(self, transcript: str, at_ms: int = 0) -> list[ContextFlag]:
        """
        Scan transcript for context flags.
        """
        if not transcript or not transcript.strip():
            return []

        norm_transcript = phonetic_key(transcript)
        transcript_tokens = set(norm_transcript.split())
        flags: list[ContextFlag] = []
        seen_categories: set[tuple[str, str]] = set()

        for cat, raw_term, lang, norm_term, is_short in self.indexed_terms:
            matched = False

            if is_short:
                # Short terms require exact word boundary / token match
                if norm_term in transcript_tokens:
                    matched = True
            else:
                # Phrase or longer term match
                if norm_term in norm_transcript or len(norm_term) >= 5 and fuzz.partial_ratio(norm_term, norm_transcript) >= 88:
                    matched = True

            if matched:
                key = (cat, raw_term)
                if key not in seen_categories:
                    seen_categories.add(key)
                    flags.append(
                        ContextFlag(
                            category=cat,
                            term=raw_term,
                            language=lang,
                            at_ms=at_ms,
                        )
                    )

        return flags
