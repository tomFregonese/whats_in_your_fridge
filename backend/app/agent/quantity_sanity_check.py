"""Deterministic, code-level guard on the quantity fields a dictated item
comes back with — same stance as `agent/stock_reference_check.py` /
`agent/allergy_check.py`: what the model *says* is never trusted outright
when it's cheap to verify against something we actually know.

Grammar-constrained JSON decoding (see `nlp/main.py`) already guarantees
the *shape* of the response is valid — but not that its *content* is
right. In practice, this small model reliably invents a plausible-looking
`quantity_unit` that was never actually said, especially on a short,
single-item transcript (empirically: "ten potatoes" -> unit "kg" or
"boîte", "milk" -> unit "L" — every observed case invented a unit with no
basis in the transcript at all). It also sometimes echoes the whole
transcript into `quantity_raw` even when `quantity_value` is already set,
contradicting its own instructions (see `nlp/main.py`'s system prompt) —
the two are meant to be mutually exclusive (see `DictatedItemArgs`'s
docstring).

Both are checked against the transcript itself / against each other here,
deterministically, rather than trusted — cheaper and more reliable than
trying to prompt-engineer a small model into never making these mistakes.
"""

import re

from app.agent.output_schema import DictatedItemArgs

# Alias groups for the units the model is asked to recognize (see
# `nlp/main.py`'s system prompt) — French and English, common written and
# spoken forms. Each group is checked as a whole: if the model's chosen
# unit is a member, any member appearing in the transcript counts as
# confirmation (so "liters" in the transcript confirms a unit of "L").
_UNIT_ALIASES: list[set[str]] = [
    {"kg", "kilo", "kilos", "kilogramme", "kilogrammes", "kilogram", "kilograms"},
    {"g", "gramme", "grammes", "gram", "grams"},
    {"l", "litre", "litres", "liter", "liters"},
    {"ml", "millilitre", "millilitres", "milliliter", "milliliters"},
    {"boîte", "boite", "boîtes", "boites", "can", "cans", "canette", "canettes"},
    {"paquet", "paquets", "pack", "packs", "packet", "packets", "sachet", "sachets"},
    {"pièce", "piece", "pièces", "pieces"},
]


def _mentioned_in(transcript: str, unit: str) -> bool:
    """Whether `unit` (or one of its aliases) appears as a whole word in
    `transcript`, case-insensitively. Deliberately exact-token matching,
    no fuzzy/partial matching: a false negative here just drops a unit
    that might actually have been said (safe — the user reviews the
    result before anything is saved), whereas a false positive would let
    a genuinely invented unit through unnoticed."""
    unit_norm = unit.strip().lower()
    group = next((g for g in _UNIT_ALIASES if unit_norm in g), {unit_norm})
    words = set(re.findall(r"[^\W\d_]+", transcript.lower(), flags=re.UNICODE))
    return bool(group & words)


def sanitize_quantities(items: list[DictatedItemArgs], transcript: str) -> None:
    """Mutates each item in place:

    - drops `quantity_unit` if it doesn't correspond to anything actually
      said in `transcript` (see `_mentioned_in`).
    - clears `quantity_raw` whenever `quantity_value` is set — the two
      are meant to be mutually exclusive.
    """
    for item in items:
        if item.quantity_unit and not _mentioned_in(transcript, item.quantity_unit):
            item.quantity_unit = None
        if item.quantity_value is not None:
            item.quantity_raw = None
