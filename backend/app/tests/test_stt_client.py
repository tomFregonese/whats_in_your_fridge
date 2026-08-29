from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.agent import stt_client
from app.services.exceptions import SttUnavailableError


def test_transcribe_returns_text_from_the_response() -> None:
    response = MagicMock()
    response.json.return_value = {"text": "two carrots and a liter of milk"}
    response.raise_for_status.return_value = None

    with patch("app.agent.stt_client.httpx.post", return_value=response) as mock_post:
        result = stt_client.transcribe(audio_base64="ZmFrZQ==", audio_format="wav")

    assert result == "two carrots and a liter of milk"
    assert mock_post.call_args.kwargs["json"] == {
        "audio_base64": "ZmFrZQ==",
        "audio_format": "wav",
    }


def test_transcribe_wraps_connection_failure() -> None:
    with (
        patch("app.agent.stt_client.httpx.post", side_effect=httpx.ConnectError("refused")),
        pytest.raises(SttUnavailableError),
    ):
        stt_client.transcribe(audio_base64="ZmFrZQ==", audio_format="wav")


def test_transcribe_wraps_non_2xx_response() -> None:
    response = MagicMock()
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500", request=MagicMock(), response=MagicMock(status_code=500)
    )

    with (
        patch("app.agent.stt_client.httpx.post", return_value=response),
        pytest.raises(SttUnavailableError),
    ):
        stt_client.transcribe(audio_base64="ZmFrZQ==", audio_format="wav")
