"""
validator.py

Validates Ethereum wallet addresses reported by victims before any
blockchain lookups are performed.

This module only checks the *structural/format* validity of an address
(and, where possible, its EIP-55 checksum). It does NOT and MUST NOT
attempt to determine who owns an address -- see project ethical
requirements.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

try:
    from web3 import Web3

    _WEB3_AVAILABLE = True
except ImportError:  # pragma: no cover - web3 is a listed dependency
    _WEB3_AVAILABLE = False

# Basic structural pattern: 0x followed by exactly 40 hex characters.
_ADDRESS_PATTERN = re.compile(r"^0x[0-9a-fA-F]{40}$")


@dataclass(frozen=True)
class ValidationResult:
    """Result of validating a wallet address."""

    address: str
    is_valid: bool
    message: str
    checksum_address: str | None = None

    def __str__(self) -> str:  # pragma: no cover - convenience only
        return self.message


def validate_wallet_address(address: str | None) -> ValidationResult:
    """
    Validate that a string is a well-formed Ethereum wallet address.

    Args:
        address: the wallet address string reported by a victim/user.
            May be None or empty.

    Returns:
        ValidationResult: contains whether the address is valid, a
        human-readable message, and (if valid and web3 is available) the
        EIP-55 checksummed version of the address.

    Notes:
        - This function performs NO network calls.
        - This function does NOT identify or infer wallet ownership.
    """
    if address is None:
        return ValidationResult(
            address="",
            is_valid=False,
            message="No wallet address was provided.",
        )

    cleaned = address.strip()

    if cleaned == "":
        return ValidationResult(
            address="",
            is_valid=False,
            message="Wallet address is empty.",
        )

    if not _ADDRESS_PATTERN.match(cleaned):
        return ValidationResult(
            address=cleaned,
            is_valid=False,
            message=(
                "Invalid Ethereum wallet address. Expected format: '0x' "
                "followed by 40 hexadecimal characters."
            ),
        )

    # Prefer web3.py's checksum validation when available, since it also
    # verifies EIP-55 mixed-case checksums (catching typos that a plain
    # regex would miss).
    if _WEB3_AVAILABLE:
        try:
            if not Web3.is_address(cleaned):
                return ValidationResult(
                    address=cleaned,
                    is_valid=False,
                    message="Invalid Ethereum wallet address.",
                )
            checksum = Web3.to_checksum_address(cleaned)
        except (ValueError, TypeError):
            return ValidationResult(
                address=cleaned,
                is_valid=False,
                message="Invalid Ethereum wallet address.",
            )

        return ValidationResult(
            address=cleaned,
            is_valid=True,
            message="Valid Ethereum wallet address.",
            checksum_address=checksum,
        )

    # Fallback path if web3 is somehow unavailable: regex match is enough
    # to consider it structurally valid.
    return ValidationResult(
        address=cleaned,
        is_valid=True,
        message="Valid Ethereum wallet address.",
        checksum_address=None,
    )
