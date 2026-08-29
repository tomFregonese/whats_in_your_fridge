from unittest.mock import patch

import pytest

from app.agent import duplicate_check
from app.services.exceptions import AgentResponseInvalidError


def test_find_duplicate_groups_returns_groups_from_the_local_service() -> None:
    raw = {"groups": [{"names": ["carottes", "carrots"], "suggested_name": "carottes"}]}

    with patch("app.agent.duplicate_check.nlp_client.find_duplicates", return_value=raw):
        groups = duplicate_check.find_duplicate_groups(
            ingredient_names=["carottes", "carrots", "lait"]
        )

    assert len(groups) == 1
    assert groups[0].names == ["carottes", "carrots"]
    assert groups[0].suggested_name == "carottes"


def test_find_duplicate_groups_raises_on_malformed_response() -> None:
    with (
        patch(
            "app.agent.duplicate_check.nlp_client.find_duplicates",
            return_value={"groups": "not-a-list"},
        ),
        pytest.raises(AgentResponseInvalidError),
    ):
        duplicate_check.find_duplicate_groups(ingredient_names=["carottes", "carrots"])


def test_find_duplicate_groups_short_circuits_below_two_names() -> None:
    with patch("app.agent.duplicate_check.nlp_client.find_duplicates") as mock_find:
        groups = duplicate_check.find_duplicate_groups(ingredient_names=["carottes"])

    assert groups == []
    mock_find.assert_not_called()


def test_find_duplicate_groups_tolerates_a_one_name_group() -> None:
    # Regression test: grammar-constrained decoding doesn't actually
    # enforce a JSON schema's `minItems` (observed against the real
    # model), so a "group" naming only one ingredient is a real
    # possibility — it must not fail parsing the rest of a response that
    # also contains valid groups.
    raw = {
        "groups": [
            {"names": ["pommes de terre"], "suggested_name": "pommes de terre"},
            {"names": ["carottes", "carrots"], "suggested_name": "carottes"},
        ]
    }

    with patch("app.agent.duplicate_check.nlp_client.find_duplicates", return_value=raw):
        groups = duplicate_check.find_duplicate_groups(
            ingredient_names=["carottes", "carrots", "pommes de terre"]
        )

    assert len(groups) == 2
    assert groups[0].names == ["pommes de terre"]
    assert groups[1].names == ["carottes", "carrots"]
