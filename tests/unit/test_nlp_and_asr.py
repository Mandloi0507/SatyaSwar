"""
Unit tests for NLP transliteration, keyword spotting, contact matching, and ASR prompt generation.
Authoritative source: Implementation.md, Section 7.7, 7.8, 7.9, 15.1
"""

import pytest

from satyaswar_ml.asr.whisper_asr import WhisperASR
from satyaswar_ml.nlp.contacts import ContactMatcher
from satyaswar_ml.nlp.keywords import KeywordMatcher
from satyaswar_ml.nlp.translit import is_devanagari, phonetic_key, transliterate_to_latin
from satyaswar_ml.schemas import Contact


class TestTransliterationAndPhoneticKeys:
    def test_devanagari_detection(self):
        assert is_devanagari("प्रिया") is True
        assert is_devanagari("Priyanka") is False
        assert is_devanagari("Hello दुनिया") is True

    def test_transliterate_devanagari_to_latin(self):
        assert "priy" in transliterate_to_latin("प्रिया").lower()
        assert "abhi" in transliterate_to_latin("अभिषेक").lower()

    def test_phonetic_key_normalization(self):
        # Long vowels to short
        assert phonetic_key("Preeti") == phonetic_key("Priti")
        assert phonetic_key("Pooja") == phonetic_key("Puja")

        # Honorific stripping
        assert phonetic_key("Priyanka Ji") == phonetic_key("Priyanka")
        assert phonetic_key("Rahul Bhai") == phonetic_key("Rahul")

        # Devanagari to Latin match
        key_deva = phonetic_key("प्रिया")
        key_latin = phonetic_key("Priya")
        assert key_deva == key_latin


class TestKeywordMatcher:
    @pytest.fixture
    def matcher(self):
        return KeywordMatcher()

    def test_english_urgency_and_money(self, matcher):
        transcript = "This is urgent, please send fifty thousand rupees right now"
        flags = matcher.scan(transcript, at_ms=1000)
        categories = {f.category for f in flags}
        assert "urgency" in categories
        assert "money" in categories

    def test_hinglish_context_flags(self, matcher):
        transcript = "Jaldi karo, kisi ko mat batana, paise bhejo"
        flags = matcher.scan(transcript, at_ms=2000)
        categories = {f.category for f in flags}
        assert "urgency" in categories
        assert "secrecy" in categories
        assert "money" in categories

    def test_devanagari_context_flags(self, matcher):
        transcript = "मैं मुसीबत में हूँ, मुझे अभी पचास हज़ार रुपये ट्रांसफर करो"
        flags = matcher.scan(transcript, at_ms=3000)
        categories = {f.category for f in flags}
        assert "urgency" in categories
        assert "money" in categories
        assert "family_emergency" in categories

    def test_short_term_exact_boundary_rule(self, matcher):
        # "hotpot" contains "otp", but should NOT trigger "otp" context flag
        flags = matcher.scan("The food is in the hotpot")
        otp_flags = [f for f in flags if f.category == "otp_credentials"]
        assert len(otp_flags) == 0

        # Isolated OTP should match
        flags_otp = matcher.scan("Please share your OTP immediately")
        otp_flags_valid = [f for f in flags_otp if f.category == "otp_credentials"]
        assert len(otp_flags_valid) > 0


class TestContactMatcher:
    @pytest.fixture
    def contacts(self):
        return [
            Contact(
                contact_id="c_01",
                display_name="Priyanka Sharma",
                aliases=["Priti", "प्रीति"],
                label="Sister",
            ),
            Contact(
                contact_id="c_02",
                display_name="Abhishek Shukla",
                aliases=["Abhi"],
                label="Colleague",
            ),
            Contact(
                contact_id="c_03",
                display_name="Rahul Verma",
                aliases=[],
                label="Manager",
            ),
            Contact(
                contact_id="c_04",
                display_name="Rahul Sharma",
                aliases=[],
                label="Friend",
            ),
        ]

    def test_exact_name_match(self, contacts):
        matcher = ContactMatcher(contacts)
        res = matcher.match("Hi, this is Abhishek Shukla calling")
        assert res.no_match is False
        assert len(res.candidates) >= 1
        assert res.candidates[0].contact_id == "c_02"
        assert res.candidates[0].score > 85.0

    def test_nickname_match(self, contacts):
        matcher = ContactMatcher(contacts)
        res = matcher.match("Hey, Priti here, please listen")
        assert res.no_match is False
        assert res.candidates[0].contact_id == "c_01"

    def test_devanagari_transcript_matches_latin_contact(self, contacts):
        matcher = ContactMatcher(contacts)
        res = matcher.match("मैं प्रिया बोल रही हूँ, तुरंत पैसे भेजो")
        assert res.no_match is False
        # Matches Priyanka Sharma
        assert res.candidates[0].contact_id == "c_01"

    def test_ambiguity_flag_on_duplicate_names(self, contacts):
        matcher = ContactMatcher(contacts)
        # Transcript mentions "Rahul" which matches both Rahul Verma and Rahul Sharma
        res = matcher.match("Hi, this is Rahul calling from the office")
        assert res.no_match is False
        assert len(res.candidates) >= 2
        assert res.ambiguous is True

    def test_zero_match(self, contacts):
        matcher = ContactMatcher(contacts)
        res = matcher.match("Good morning, I am calling from Bangalore Electricity Board")
        assert res.no_match is True
        assert len(res.candidates) == 0

    def test_empty_transcript(self, contacts):
        matcher = ContactMatcher(contacts)
        res = matcher.match("")
        assert res.no_match is True


class TestWhisperASRPrompt:
    def test_prompt_biasing_builder(self):
        contacts = [
            Contact(contact_id="1", display_name="Priyanka Sharma", aliases=["Priti", "प्रीति"]),
            Contact(contact_id="2", display_name="Abhishek Shukla", aliases=[]),
        ]
        asr = WhisperASR(model_size="small")
        prompt = asr.build_initial_prompt(contacts)
        assert "Priyanka Sharma" in prompt
        assert "Priti" in prompt
        assert "प्रीति" in prompt
        assert "Abhishek Shukla" in prompt
