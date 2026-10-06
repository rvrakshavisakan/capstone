"""Tests for app.transaction_processor."""

from app.transaction_processor import (
    determine_direction,
    process_transactions,
    unix_to_utc_string,
    wei_to_eth,
)

WALLET = "0xSUSPECT0000000000000000000000000000000A"
WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
WALLET_B = "0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"


def test_wei_to_eth_conversion():
    assert wei_to_eth("1000000000000000000") == 1.0
    assert wei_to_eth("2500000000000000000") == 2.5


def test_wei_to_eth_handles_none_and_invalid():
    assert wei_to_eth(None) == 0.0
    assert wei_to_eth("not_a_number") == 0.0


def test_unix_to_utc_string_conversion():
    # 1700000000 -> 2023-11-14 22:13:20 UTC
    result = unix_to_utc_string("1700000000")
    assert result == "2023-11-14 22:13:20"


def test_unix_to_utc_string_handles_invalid():
    assert unix_to_utc_string(None) == "unknown"
    assert unix_to_utc_string("not_a_timestamp") == "unknown"


def test_determine_direction_incoming():
    assert determine_direction(WALLET_A, WALLET, WALLET) == "incoming"


def test_determine_direction_outgoing():
    assert determine_direction(WALLET, WALLET_B, WALLET) == "outgoing"


def test_determine_direction_self():
    assert determine_direction(WALLET, WALLET, WALLET) == "self"


def test_determine_direction_unrelated():
    assert determine_direction(WALLET_A, WALLET_B, WALLET) == "unrelated"


def test_determine_direction_case_insensitive():
    assert determine_direction(WALLET_A.lower(), WALLET.upper(), WALLET) == "incoming"


def _raw_tx(tx_hash, from_addr, to_addr, block, value="1000000000000000000"):
    return {
        "hash": tx_hash,
        "from": from_addr,
        "to": to_addr,
        "value": value,
        "timeStamp": "1700000000",
        "blockNumber": str(block),
        "gas": "21000",
        "gasPrice": "50000000000",
    }


def test_process_transactions_basic_fields():
    raw = [_raw_tx("0xHASH1", WALLET_A, WALLET, 100)]
    processed = process_transactions(raw, wallet=WALLET)
    assert len(processed) == 1
    tx = processed[0]
    assert tx.transaction_hash == "0xHASH1"
    assert tx.value_eth == 1.0
    assert tx.direction == "incoming"
    assert tx.block_number == 100


def test_process_transactions_removes_duplicates():
    raw = [
        _raw_tx("0xHASH1", WALLET_A, WALLET, 100),
        _raw_tx("0xHASH1", WALLET_A, WALLET, 100),  # duplicate hash
        _raw_tx("0xHASH2", WALLET, WALLET_B, 101),
    ]
    processed = process_transactions(raw, wallet=WALLET)
    hashes = [tx.transaction_hash for tx in processed]
    assert hashes.count("0xHASH1") == 1
    assert len(processed) == 2


def test_process_transactions_sorted_chronologically():
    raw = [
        _raw_tx("0xHASH2", WALLET, WALLET_B, 200),
        _raw_tx("0xHASH1", WALLET_A, WALLET, 100),
    ]
    processed = process_transactions(raw, wallet=WALLET)
    assert [tx.block_number for tx in processed] == [100, 200]


def test_process_transactions_skips_malformed_records():
    raw = [
        {"from": WALLET_A, "to": WALLET},  # missing "hash" entirely
        _raw_tx("0xHASH1", WALLET_A, WALLET, 100),
    ]
    processed = process_transactions(raw, wallet=WALLET)
    assert len(processed) == 1
    assert processed[0].transaction_hash == "0xHASH1"


def test_process_transactions_handles_missing_numeric_fields_safely():
    raw = [
        {
            "hash": "0xHASH1",
            "from": WALLET_A,
            "to": WALLET,
            "value": None,
            "timeStamp": None,
            "blockNumber": None,
            "gas": None,
            "gasPrice": None,
        }
    ]
    processed = process_transactions(raw, wallet=WALLET)
    tx = processed[0]
    assert tx.value_eth == 0.0
    assert tx.timestamp == "unknown"
    assert tx.block_number == 0
    assert tx.gas == 0
    assert tx.gas_price == 0


def test_process_transactions_empty_history():
    assert process_transactions([], wallet=WALLET) == []
