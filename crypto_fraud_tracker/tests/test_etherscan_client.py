"""
Tests for app.etherscan_client.

All tests use mocked HTTP responses (via unittest.mock) -- no real
Etherscan API key or network access is required to run these tests.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from app.config import Settings
from app.etherscan_client import EtherscanClient, EtherscanError


def _settings():
    return Settings(etherscan_api_key="test_key_123", max_retries=2, retry_backoff_seconds=0)


def _mock_response(status_code=200, json_data=None, text=""):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.text = text
    if json_data is not None:
        resp.json.return_value = json_data
    else:
        resp.json.side_effect = ValueError("no json")
    return resp


def test_get_transactions_returns_list_on_success():
    client = EtherscanClient(settings=_settings())
    payload = {
        "status": "1",
        "message": "OK",
        "result": [{"hash": "0xHASH1"}, {"hash": "0xHASH2"}],
    }
    with patch.object(
        client._session, "get", return_value=_mock_response(200, payload)
    ):
        txs = client.get_transactions("0xSUSPECT")
    assert len(txs) == 2
    assert txs[0]["hash"] == "0xHASH1"


def test_get_transactions_handles_empty_history():
    client = EtherscanClient(settings=_settings())
    payload = {"status": "0", "message": "No transactions found", "result": []}
    with patch.object(
        client._session, "get", return_value=_mock_response(200, payload)
    ):
        txs = client.get_transactions("0xSUSPECT")
    assert txs == []


def test_get_transactions_raises_on_api_error_message():
    client = EtherscanClient(settings=_settings())
    payload = {"status": "0", "message": "NOTOK", "result": "Invalid API Key"}
    with patch.object(
        client._session, "get", return_value=_mock_response(200, payload)
    ):
        with pytest.raises(EtherscanError):
            client.get_transactions("0xSUSPECT")


def test_get_transactions_raises_on_http_error():
    client = EtherscanClient(settings=_settings())
    with patch.object(
        client._session, "get", return_value=_mock_response(500, text="Server Error")
    ):
        with pytest.raises(EtherscanError):
            client.get_transactions("0xSUSPECT")


def test_get_transactions_raises_on_malformed_json():
    client = EtherscanClient(settings=_settings())
    with patch.object(
        client._session, "get", return_value=_mock_response(200, json_data=None)
    ):
        with pytest.raises(EtherscanError):
            client.get_transactions("0xSUSPECT")


def test_get_transactions_raises_on_network_error():
    client = EtherscanClient(settings=_settings())
    with patch.object(
        client._session,
        "get",
        side_effect=requests.exceptions.ConnectionError("network down"),
    ):
        with pytest.raises(EtherscanError):
            client.get_transactions("0xSUSPECT")


def test_get_transactions_retries_then_succeeds_after_rate_limit():
    client = EtherscanClient(settings=_settings())
    payload = {"status": "1", "message": "OK", "result": [{"hash": "0xHASH1"}]}
    responses = [_mock_response(429, text="rate limited"), _mock_response(200, payload)]
    with patch.object(client._session, "get", side_effect=responses):
        txs = client.get_transactions("0xSUSPECT")
    assert len(txs) == 1
