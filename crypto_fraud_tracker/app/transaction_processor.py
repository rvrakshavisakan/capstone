"""
transaction_processor.py

Converts raw Etherscan transaction dictionaries into a clean, consistent
internal representation used by the rest of Member 1's pipeline (CSV
export, tracing, graph building).

This module performs no network I/O and no fraud/risk analysis -- it is
pure data transformation.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any

# 1 ETH = 10^18 Wei.
_WEI_PER_ETH = 10**18


@dataclass(frozen=True)
class ProcessedTransaction:
    """A cleaned, analysis-ready representation of one Ethereum transaction."""

    transaction_id: str
    from_address: str
    to_address: str
    value_eth: float
    timestamp: str  # UTC, "YYYY-MM-DD HH:MM:SS"
    block_number: int
    gas: int
    gas_price: int
    direction: str  # "incoming", "outgoing", or "self"

    def as_dict(self) -> dict[str, Any]:
        """Return this transaction as a plain dictionary (for CSV/DB export)."""
        return asdict(self)


def wei_to_eth(value_wei: str | int | float | None) -> float:
    """
    Convert a Wei amount (as returned by Etherscan, typically a string)
    into ETH as a float.

    Args:
        value_wei: the amount in Wei. Accepts str/int/float, or None.

    Returns:
        The equivalent amount in ETH. Returns 0.0 for missing/invalid input.
    """
    if value_wei is None:
        return 0.0
    try:
        return float(value_wei) / _WEI_PER_ETH
    except (TypeError, ValueError):
        return 0.0


def unix_to_utc_string(timestamp: str | int | float | None) -> str:
    """
    Convert a Unix timestamp (seconds since epoch) into a readable UTC
    datetime string of the form "YYYY-MM-DD HH:MM:SS".

    Args:
        timestamp: Unix timestamp as returned by Etherscan (usually a
            string), or None.

    Returns:
        A formatted UTC datetime string. Returns "unknown" if the input
        is missing or cannot be parsed.
    """
    if timestamp is None:
        return "unknown"
    try:
        dt = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return "unknown"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def determine_direction(from_address: str, to_address: str, wallet: str) -> str:
    """
    Determine the direction of a transaction relative to the investigated
    (suspect) wallet.

    Args:
        from_address: sender address of the transaction.
        to_address: recipient address of the transaction.
        wallet: the wallet address being investigated.

    Returns:
        "incoming" if funds moved into `wallet`, "outgoing" if funds moved
        out of `wallet`, or "self" if the wallet sent to itself.
    """
    from_norm = (from_address or "").lower()
    to_norm = (to_address or "").lower()
    wallet_norm = (wallet or "").lower()

    is_sender = from_norm == wallet_norm
    is_receiver = to_norm == wallet_norm

    if is_sender and is_receiver:
        return "self"
    if is_receiver:
        return "incoming"
    if is_sender:
        return "outgoing"
    return "unrelated"


def process_transactions(
    raw_transactions: list[dict[str, Any]],
    wallet: str,
) -> list[ProcessedTransaction]:
    """
    Clean, normalise, deduplicate, and sort a list of raw Etherscan
    transactions for a given investigated wallet.

    Steps performed:
        1. Skip malformed records that are missing a transaction hash.
        2. Convert Wei -> ETH and Unix timestamp -> UTC datetime string.
        3. Compute `direction` relative to `wallet`.
        4. Remove duplicate transaction hashes (keeping the first seen).
        5. Sort chronologically by block number (ascending).

    Args:
        raw_transactions: list of raw transaction dicts from Etherscan.
        wallet: the wallet address being investigated (used to compute
            direction).

    Returns:
        A list of ProcessedTransaction objects, sorted chronologically,
        with duplicates removed.
    """
    seen_hashes: set[str] = set()
    processed: list[ProcessedTransaction] = []

    for raw in raw_transactions:
        if not isinstance(raw, dict):
            continue

        tx_hash = raw.get("hash")
        if not tx_hash:
            # Malformed record with no transaction hash -- skip safely.
            continue
        if tx_hash in seen_hashes:
            continue

        from_address = raw.get("from", "") or ""
        to_address = raw.get("to", "") or ""

        try:
            block_number = int(raw.get("blockNumber", 0) or 0)
        except (TypeError, ValueError):
            block_number = 0

        try:
            gas = int(raw.get("gas", 0) or 0)
        except (TypeError, ValueError):
            gas = 0

        try:
            gas_price = int(raw.get("gasPrice", 0) or 0)
        except (TypeError, ValueError):
            gas_price = 0

        processed.append(
            ProcessedTransaction(
                transaction_id=tx_hash,
                from_address=from_address,
                to_address=to_address,
                value_eth=wei_to_eth(raw.get("value")),
                timestamp=unix_to_utc_string(raw.get("timeStamp")),
                block_number=block_number,
                gas=gas,
                gas_price=gas_price,
                direction=determine_direction(from_address, to_address, wallet),
            )
        )
        seen_hashes.add(tx_hash)

    processed.sort(key=lambda tx: tx.block_number)
    return processed

