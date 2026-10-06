"""Tests for app.validator -- wallet address validation."""

from app.validator import validate_wallet_address

VALID_ADDRESS = "0x1234567890AbCdEf1234567890aBcDeF12345678"  # 40 hex chars
VALID_ADDRESS_LOWER = VALID_ADDRESS.lower()


def test_valid_wallet_address():
    result = validate_wallet_address(VALID_ADDRESS)
    assert result.is_valid is True
    assert result.message == "Valid Ethereum wallet address."


def test_valid_wallet_address_lowercase_is_still_valid():
    result = validate_wallet_address(VALID_ADDRESS_LOWER)
    assert result.is_valid is True


def test_invalid_wallet_address_too_short():
    result = validate_wallet_address("0x123456")
    assert result.is_valid is False


def test_invalid_wallet_address_wrong_prefix():
    bad = "742d35Cc6634C0532925a3b844Bc454e4438f44"  # missing 0x
    result = validate_wallet_address(bad)
    assert result.is_valid is False


def test_invalid_wallet_address_non_hex_characters():
    bad = "0xZZZZ35Cc6634C0532925a3b844Bc454e4438f44"
    result = validate_wallet_address(bad)
    assert result.is_valid is False


def test_empty_wallet_address():
    result = validate_wallet_address("")
    assert result.is_valid is False
    assert "empty" in result.message.lower()


def test_none_wallet_address():
    result = validate_wallet_address(None)
    assert result.is_valid is False


def test_whitespace_only_wallet_address():
    result = validate_wallet_address("    ")
    assert result.is_valid is False
