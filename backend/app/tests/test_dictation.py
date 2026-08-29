from unittest.mock import patch

import pytest

from app.agent import dictation
from app.services.exceptions import AgentResponseInvalidError


def test_parse_transcript_returns_items_from_the_local_service() -> None:
    raw = {
        "items": [
            {
                "ingredient_name": "carrot",
                "quantity_value": 2,
                "quantity_unit": "pcs",
                "quantity_raw": None,
            }
        ]
    }

    with patch("app.agent.dictation.nlp_client.structure", return_value=raw):
        items = dictation.parse_transcript(transcript="two carrots")

    assert len(items) == 1
    assert items[0].ingredient_name == "carrot"
    assert items[0].quantity_value == 2


def test_parse_transcript_sanitizes_a_hallucinated_unit() -> None:
    # Regression test: end-to-end through parse_transcript(), not just
    # sanitize_quantities() in isolation — the local model reliably
    # invents a unit on a short transcript like this one.
    raw = {
        "items": [
            {
                "ingredient_name": "potatoes",
                "quantity_value": 10,
                "quantity_unit": "kg",
                "quantity_raw": "ten potatoes",
            }
        ]
    }

    with patch("app.agent.dictation.nlp_client.structure", return_value=raw):
        items = dictation.parse_transcript(transcript="ten potatoes")

    assert items[0].quantity_unit is None
    assert items[0].quantity_raw is None
    assert items[0].quantity_value == 10


def test_parse_transcript_raises_on_malformed_response() -> None:
    with (
        patch("app.agent.dictation.nlp_client.structure", return_value={"items": "not-a-list"}),
        pytest.raises(AgentResponseInvalidError),
    ):
        dictation.parse_transcript(transcript="two carrots")
