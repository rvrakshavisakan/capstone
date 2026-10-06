"""
etherscan_client.py

Thin, well-behaved wrapper around the public Etherscan API.

Responsibilities:
    - Build and send HTTP requests to Etherscan.
    - Handle HTTP errors, network errors, API-level errors, rate limits,
      and malformed JSON responses.
    - Return raw (but sanity-checked) transaction data as a list of
      dictionaries, in the exact shape Etherscan provides.

This module deliberately does NOT interpret, clean, or transform the
data -- that is transaction_processor.py's job. Keeping API concerns and
data-processing concerns separate makes both easier to test and to
explain during a viva.
"""

from __future__ import annotations

import time
from typing import Any

import requests

from crypto_fraud_tracker.app.config import Settings, get_settings


class EtherscanError(Exception):
    """Raised for any Etherscan API-level or transport-level failure."""


class EtherscanClient:
    """A small client for the Etherscan 'account' API endpoints."""

    def __init__(self, settings: Settings | None = None) -> None:
        """
        Args:
            settings: optional pre-built Settings object (useful for
                tests). If omitted, settings are loaded from the
                environment via get_settings().
        """
        self._settings = settings or get_settings()
        self._session = requests.Session()

    def get_transactions(
        self,
        wallet_address: str,
        start_block: int = 0,
        end_block: int = 99_999_999,
        page: int = 1,
        offset: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        Retrieve normal (external) Ethereum transactions for a wallet.

        Args:
            wallet_address: the Ethereum address to query.
            start_block: first block to include (default: genesis).
            end_block: last block to include (default: a far-future block).
            page: pagination page number (Etherscan paginates results).
            offset: number of records per page (Etherscan max is 10000).

        Returns:
            A list of raw transaction dictionaries exactly as returned by
            Etherscan's "txlist" action. Returns an empty list if the
            wallet has no transaction history.

        Raises:
            EtherscanError: on HTTP failure, network failure, malformed
                JSON, an Etherscan-reported API error (other than "no
                transactions found"), or a rate-limit response.
        """
        params = {
            "chainid": "11155111",
            "module": "account",
            "action": "txlist",
            "address": wallet_address,
            "startblock": start_block,
            "endblock": end_block,
            "page": page,
            "offset": offset,
            "sort": "asc",
            "apikey": self._settings.etherscan_api_key,
        }

        payload = self._request_with_retry(params)
        return self._extract_result_list(payload)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _request_with_retry(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Perform the HTTP GET request, retrying on transient failures.

        Handles connection errors, timeouts, and HTTP 429 (rate limit)
        with a simple linear backoff. Raises EtherscanError once retries
        are exhausted.
        """
        last_error: Exception | None = None

        for attempt in range(1, self._settings.max_retries + 1):
            try:
                response = self._session.get(
                    self._settings.etherscan_base_url,
                    params=params,
                    timeout=self._settings.request_timeout_seconds,
                )
            except requests.exceptions.Timeout as exc:
                last_error = EtherscanError(
                    f"Request to Etherscan timed out (attempt {attempt})."
                )
                last_error.__cause__ = exc
            except requests.exceptions.ConnectionError as exc:
                last_error = EtherscanError(
                    f"Network error contacting Etherscan (attempt {attempt})."
                )
                last_error.__cause__ = exc
            except requests.exceptions.RequestException as exc:
                # Catch-all for any other requests-library failure.
                raise EtherscanError(f"Request to Etherscan failed: {exc}") from exc
            else:
                if response.status_code == 429:
                    last_error = EtherscanError(
                        "Etherscan API rate limit exceeded (HTTP 429)."
                    )
                elif response.status_code != 200:
                    raise EtherscanError(
                        f"Etherscan API returned HTTP {response.status_code}: "
                        f"{response.text[:200]}"
                    )
                else:
                    return self._parse_json(response)

            # Backoff before retrying (only reached on timeout/conn-error/429).
            if attempt < self._settings.max_retries:
                time.sleep(self._settings.retry_backoff_seconds * attempt)

        assert last_error is not None
        raise last_error

    @staticmethod
    def _parse_json(response: requests.Response) -> dict[str, Any]:
        """Safely parse a response body as JSON."""
        try:
            return response.json()
        except ValueError as exc:
            raise EtherscanError(
                "Etherscan returned malformed JSON that could not be parsed."
            ) from exc

    @staticmethod
    def _extract_result_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Pull the transaction list out of an Etherscan response payload,
        handling Etherscan's various "status"/"message" error conventions.

        Etherscan encodes both success and "no data" as different
        combinations of status/message/result, so this needs to be
        handled carefully rather than assuming result is always a list.
        """
        if not isinstance(payload, dict):
            raise EtherscanError("Unexpected Etherscan response format.")

        status = str(payload.get("status", ""))
        message = str(payload.get("message", ""))
        result = payload.get("result")

        # Etherscan's documented convention: status "0" + message
        # "No transactions found" is NOT an error -- it just means the
        # wallet has no transaction history.
        if status == "0":
            if message.strip().lower() == "no transactions found":
                return []
            # Any other status "0" message is a genuine API-level error,
            # e.g. invalid API key, invalid address, rate limit notice
            # embedded in the JSON body instead of the HTTP status code.
            raise EtherscanError(f"Etherscan API error: {message or result}")

        if not isinstance(result, list):
            raise EtherscanError(
                "Etherscan response did not contain a transaction list."
            )

        return result

