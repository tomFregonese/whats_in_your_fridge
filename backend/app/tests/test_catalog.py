from collections.abc import Iterator, Mapping
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.agent import catalog
from app.services.exceptions import CatalogUnavailableError

FAKE_PAYLOAD = {
    "data": [
        {
            "id": "foo/bar:free",
            "name": "Foo Bar (free)",
            "context_length": 8192,
            "description": "d",
        },
        {"id": "foo/baz", "name": "Foo Baz (paid)", "context_length": 4096, "description": None},
        {"id": "qux/quux:free"},
    ]
}


def _mock_response(payload: Mapping[str, object]) -> MagicMock:
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


@pytest.fixture(name="mock_get")
def mock_get_fixture() -> Iterator[MagicMock]:
    with patch("app.agent.catalog.httpx.get", return_value=_mock_response(FAKE_PAYLOAD)) as mock:
        yield mock


def test_list_free_models_filters_out_non_free_entries(mock_get: MagicMock) -> None:
    models = catalog.list_free_models()

    assert [m.id for m in models] == ["foo/bar:free", "qux/quux:free"]


def test_list_free_models_defaults_name_to_id_when_missing(mock_get: MagicMock) -> None:
    models = catalog.list_free_models()

    qux = next(m for m in models if m.id == "qux/quux:free")
    assert qux.name == "qux/quux:free"
    assert qux.context_length is None


def test_list_free_models_caches_between_calls(mock_get: MagicMock) -> None:
    catalog.list_free_models()
    catalog.list_free_models()

    mock_get.assert_called_once()


def test_list_free_models_force_refresh_bypasses_cache(mock_get: MagicMock) -> None:
    catalog.list_free_models()
    catalog.list_free_models(force_refresh=True)

    assert mock_get.call_count == 2


def test_list_free_models_wraps_http_errors() -> None:
    with (
        patch("app.agent.catalog.httpx.get", side_effect=httpx.ConnectError("boom")),
        pytest.raises(CatalogUnavailableError),
    ):
        catalog.list_free_models()
