from __future__ import annotations

import os
import re
import time
from difflib import SequenceMatcher
from functools import lru_cache
from itertools import islice

from spylls.hunspell import Dictionary

TOKEN_RE = re.compile(r"[A-Za-zА-Яа-яЁё'-]+")
CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
LATIN_RE = re.compile(r"[A-Za-z]")


@lru_cache(maxsize=1)
def load_dictionaries() -> dict[str, Dictionary]:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dictionaries"))
    return {
        "ru": Dictionary.from_files(os.path.join(base_dir, "ru_RU")),
        "en": Dictionary.from_files(os.path.join(base_dir, "en_US")),
    }


class SpellCheckService:
    def __init__(self) -> None:
        self.dictionaries = load_dictionaries()
        self.simulated_delay_seconds = float(os.getenv("SPELLCHECK_DELAY_SECONDS", "3"))

    def check_text(self, text: str, language: str = "auto") -> dict:
        time.sleep(self.simulated_delay_seconds)

        misspellings: list[dict] = []
        replacements: list[tuple[int, int, str]] = []

        for match in TOKEN_RE.finditer(text):
            token = match.group(0)
            detected_language = self.detect_language(token, preferred=language)

            if detected_language not in {"ru", "en"}:
                continue

            dictionary = self.dictionaries[detected_language]
            normalized = token.lower()

            if dictionary.lookup(normalized):
                continue

            suggestions = self.rank_suggestions(normalized, dictionary)
            replacement = self.apply_case(suggestions[0], token) if suggestions else token

            misspellings.append(
                {
                    "word": token,
                    "start": match.start(),
                    "end": match.end(),
                    "detected_language": detected_language,
                    "suggestions": [self.apply_case(s, token) for s in suggestions],
                }
            )
            replacements.append((match.start(), match.end(), replacement))

        corrected_text = self.build_corrected_text(text, replacements)
        return {
            "original_text": text,
            "corrected_text": corrected_text,
            "total_words": len(TOKEN_RE.findall(text)),
            "mistakes_count": len(misspellings),
            "misspellings": misspellings,
        }


    def rank_suggestions(self, normalized: str, dictionary: Dictionary) -> list[str]:
        raw_suggestions = list(islice(dictionary.suggest(normalized), 12))
        ranked = sorted(
            raw_suggestions,
            key=lambda candidate: (
                self.non_letter_penalty(candidate),
                abs(len(candidate) - len(normalized)),
                -self.common_prefix_len(normalized, candidate),
                -self.common_suffix_len(normalized, candidate),
                self.edit_distance(normalized, candidate),
                -SequenceMatcher(None, normalized, candidate).ratio(),
            ),
        )
        deduplicated: list[str] = []
        for candidate in ranked:
            if candidate not in deduplicated:
                deduplicated.append(candidate)
        return deduplicated[:5]


    @staticmethod
    def non_letter_penalty(value: str) -> int:
        return sum(1 for char in value if not char.isalpha())

    @staticmethod
    def common_prefix_len(left: str, right: str) -> int:
        count = 0
        for left_char, right_char in zip(left, right):
            if left_char != right_char:
                break
            count += 1
        return count

    @staticmethod
    def common_suffix_len(left: str, right: str) -> int:
        count = 0
        for left_char, right_char in zip(reversed(left), reversed(right)):
            if left_char != right_char:
                break
            count += 1
        return count

    @staticmethod
    def edit_distance(left: str, right: str) -> int:
        if left == right:
            return 0
        if not left:
            return len(right)
        if not right:
            return len(left)

        previous = list(range(len(right) + 1))
        for i, left_char in enumerate(left, start=1):
            current = [i]
            for j, right_char in enumerate(right, start=1):
                insert_cost = current[j - 1] + 1
                delete_cost = previous[j] + 1
                replace_cost = previous[j - 1] + (left_char != right_char)
                current.append(min(insert_cost, delete_cost, replace_cost))
            previous = current
        return previous[-1]

    @staticmethod
    def detect_language(token: str, preferred: str = "auto") -> str:
        if preferred in {"ru", "en"}:
            return preferred
        if CYRILLIC_RE.search(token):
            return "ru"
        if LATIN_RE.search(token):
            return "en"
        return "unknown"

    @staticmethod
    def apply_case(suggestion: str, original: str) -> str:
        if original.isupper():
            return suggestion.upper()
        if original.istitle():
            return suggestion.title()
        return suggestion

    @staticmethod
    def build_corrected_text(text: str, replacements: list[tuple[int, int, str]]) -> str:
        if not replacements:
            return text

        parts: list[str] = []
        previous_end = 0
        for start, end, replacement in replacements:
            parts.append(text[previous_end:start])
            parts.append(replacement)
            previous_end = end
        parts.append(text[previous_end:])
        return "".join(parts)
