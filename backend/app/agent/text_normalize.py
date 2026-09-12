"""Tiny shared text-normalization helper used by every deterministic,
code-level check that compares a household list (allergies, equipment)
against something the LLM reported — see `agent/allergy_check.py` and
`agent/equipment_check.py`.
"""

import unicodedata


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return without_accents.casefold().strip()
