from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.agent import nlp_client
from app.services.exceptions import NlpUnavailableError


def test_structure_returns_parsed_json_from_the_response() -> None:
    payload = {
        "items": [
            {
                "ingredient_name": "carrot",
                "quantity_value": 2,
                "quantity_unit": None,
                "quantity_raw": None,
            }
        ]
    }
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None

    with patch("app.agent.nlp_client.httpx.post", return_value=response) as mock_post:
        result = nlp_client.structure(transcript="two carrots")

    assert result == payload
    assert mock_post.call_args.kwargs["json"] == {"transcript": "two carrots"}


def test_structure_wraps_connection_failure() -> None:
    with (
        patch("app.agent.nlp_client.httpx.post", side_effect=httpx.ConnectError("refused")),
        pytest.raises(NlpUnavailableError),
    ):
        nlp_client.structure(transcript="two carrots")


def test_structure_wraps_non_2xx_response() -> None:
    response = MagicMock()
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500", request=MagicMock(), response=MagicMock(status_code=500)
    )

    with (
        patch("app.agent.nlp_client.httpx.post", return_value=response),
        pytest.raises(NlpUnavailableError),
    ):
        nlp_client.structure(transcript="two carrots")


def test_find_duplicates_returns_parsed_json_from_the_response() -> None:
    response = MagicMock()
    response.json.return_value = {
        "groups": [{"names": ["carottes", "carrots"], "suggested_name": "carottes"}]
    }
    response.raise_for_status.return_value = None

    with patch("app.agent.nlp_client.httpx.post", return_value=response) as mock_post:
        result = nlp_client.find_duplicates(ingredient_names=["carottes", "carrots", "lait"])

    assert result == {
        "groups": [{"names": ["carottes", "carrots"], "suggested_name": "carottes"}]
    }
    assert mock_post.call_args.kwargs["json"] == {
        "ingredient_names": ["carottes", "carrots", "lait"]
    }


def test_find_duplicates_wraps_connection_failure() -> None:
    with (
        patch("app.agent.nlp_client.httpx.post", side_effect=httpx.ConnectError("refused")),
        pytest.raises(NlpUnavailableError),
    ):
        nlp_client.find_duplicates(ingredient_names=["carottes", "carrots"])


def test_find_duplicates_wraps_non_2xx_response() -> None:
    response = MagicMock()
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500", request=MagicMock(), response=MagicMock(status_code=500)
    )

    with (
        patch("app.agent.nlp_client.httpx.post", return_value=response),
        pytest.raises(NlpUnavailableError),
    ):
        nlp_client.find_duplicates(ingredient_names=["carottes", "carrots"])
