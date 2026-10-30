"""
Claimed-identity contact candidate ranking.
Authoritative source: Implementation.md, Section 7.9

Ranks caller contacts against spoken transcript:
- Phonetic normalisation across Latin and Devanagari.
- N-gram sliding window matching with Rapidfuzz.
- Ambiguity and no-match detection.
- NEVER auto-selects; suggestions only.
"""

from __future__ import annotations

from rapidfuzz import fuzz

from satyaswar_ml.nlp.translit import phonetic_key
from satyaswar_ml.schemas import ClaimCandidate, ClaimEvent, Contact


class ContactMatcher:
    """
    Fuzzy and phonetic contact identity matcher.
    """

    def __init__(self, contacts: list[Contact], min_score: float = 75.0):
        self.contacts = contacts
        self.min_score = min_score

        # Precompute search keys for each contact
        # Map: contact -> list of (raw_label, phonetic_key)
        self.contact_keys: list[tuple[Contact, list[tuple[str, str]]]] = []
        for c in contacts:
            keys: list[tuple[str, str]] = []
            # Display name
            norm_disp = phonetic_key(c.display_name)
            if norm_disp:
                keys.append((c.display_name, norm_disp))
                # Individual name tokens (e.g. "Priyanka" from "Priyanka Sharma")
                for tok in norm_disp.split():
                    if len(tok) >= 3 and tok != norm_disp:
                        keys.append((tok, tok))

            # Aliases
            for alias in c.aliases:
                norm_alias = phonetic_key(alias)
                if norm_alias:
                    keys.append((alias, norm_alias))
                    for tok in norm_alias.split():
                        if len(tok) >= 3 and tok != norm_alias:
                            keys.append((tok, tok))

            self.contact_keys.append((c, keys))

    def match(self, transcript: str, call_id: str = "adhoc") -> ClaimEvent:
        """
        Match transcript against registered contacts.
        """
        if not transcript or not transcript.strip() or not self.contacts:
            return ClaimEvent(
                call_id=call_id,
                candidates=[],
                ambiguous=False,
                no_match=True,
            )

        norm_transcript = phonetic_key(transcript)
        words = norm_transcript.split()
        if not words:
            return ClaimEvent(
                call_id=call_id,
                candidates=[],
                ambiguous=False,
                no_match=True,
            )

        # Generate 1-gram, 2-gram, and 3-gram phrases from transcript
        ngrams: list[str] = []
        n_words = len(words)
        for k in range(1, min(4, n_words + 1)):
            for i in range(n_words - k + 1):
                ngrams.append(" ".join(words[i:i + k]))

        scored_candidates: list[tuple[Contact, str, float]] = []

        for contact, keys in self.contact_keys:
            best_score = 0.0
            best_matched_on = ""

            for raw_label, p_key in keys:
                # Compare against all transcript n-grams
                for ng in ngrams:
                    r1 = fuzz.ratio(p_key, ng)
                    r2 = fuzz.token_sort_ratio(p_key, ng)
                    max_r = max(r1, r2)

                    # Indian root name / nickname prefix matching (e.g. Priy -> Priyanka, Abhi -> Abhishek)
                    if min(len(p_key), len(ng)) >= 4 and (p_key.startswith(ng) or ng.startswith(p_key)):
                        max_r = max(max_r, 85.0)

                    if max_r > best_score:
                        best_score = float(max_r)
                        best_matched_on = raw_label

            if best_score >= self.min_score:
                scored_candidates.append((contact, best_matched_on, best_score))

        # Sort descending by score
        scored_candidates.sort(key=lambda x: x[2], reverse=True)

        if not scored_candidates:
            return ClaimEvent(
                call_id=call_id,
                candidates=[],
                ambiguous=False,
                no_match=True,
            )

        # Build candidate list
        candidates: list[ClaimCandidate] = []
        top_candidates = scored_candidates[:5]
        for rank_idx, (c, matched_on, score) in enumerate(top_candidates, start=1):
            candidates.append(
                ClaimCandidate(
                    contact_id=c.contact_id,
                    matched_on=matched_on,
                    score=round(score, 1),
                    rank=rank_idx,
                )
            )

        # Check ambiguity
        ambiguous = False
        if len(candidates) >= 2:
            # Within 5 points of each other
            if abs(candidates[0].score - candidates[1].score) <= 5.0:
                ambiguous = True

        return ClaimEvent(
            call_id=call_id,
            candidates=candidates,
            ambiguous=ambiguous,
            no_match=False,
        )
