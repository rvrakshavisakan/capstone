"""Tests for app.csv_exporter."""

import csv

from app.csv_exporter import (
    FUND_FLOW_CSV_COLUMNS,
    TRANSACTIONS_CSV_COLUMNS,
    export_fund_flow_csv,
    export_transactions_csv,
)
from app.transaction_processor import ProcessedTransaction
from app.transaction_tracer import FundFlowEdge


def _sample_transaction():
    return ProcessedTransaction(
        transaction_hash="0xHASH1",
        from_address="0xAAA",
        to_address="0xSUSPECT",
        value_eth=2.0,
        timestamp="2026-09-07 10:20:00",
        block_number=230001,
        gas=21000,
        gas_price=50_000_000_000,
        direction="incoming",
    )


def _sample_edge():
    return FundFlowEdge(
        source_wallet="0xSUSPECT",
        destination_wallet="0xBBB",
        amount_eth=1.5,
        hop=1,
        transaction_hash="0xHASH2",
        timestamp="2026-09-07 10:25:00",
    )


def test_export_transactions_csv_creates_file_with_correct_columns(tmp_path):
    output_path = tmp_path / "data" / "transactions.csv"
    export_transactions_csv([_sample_transaction()], output_path)

    assert output_path.exists()

    with open(output_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == TRANSACTIONS_CSV_COLUMNS
        rows = list(reader)

    assert len(rows) == 1
    assert rows[0]["transaction_hash"] == "0xHASH1"
    assert rows[0]["direction"] == "incoming"


def test_export_transactions_csv_creates_parent_directory(tmp_path):
    output_path = tmp_path / "nested" / "dir" / "transactions.csv"
    export_transactions_csv([_sample_transaction()], output_path)
    assert output_path.parent.exists()
    assert output_path.exists()


def test_export_transactions_csv_writes_header_even_when_empty(tmp_path):
    output_path = tmp_path / "transactions.csv"
    export_transactions_csv([], output_path)

    with open(output_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == TRANSACTIONS_CSV_COLUMNS
        rows = list(reader)
    assert rows == []


def test_export_fund_flow_csv_creates_file_with_correct_columns(tmp_path):
    output_path = tmp_path / "fund_flow.csv"
    export_fund_flow_csv([_sample_edge()], output_path)

    with open(output_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == FUND_FLOW_CSV_COLUMNS
        rows = list(reader)

    assert len(rows) == 1
    assert rows[0]["source_wallet"] == "0xSUSPECT"
    assert rows[0]["destination_wallet"] == "0xBBB"
    assert rows[0]["hop"] == "1"


def test_export_fund_flow_csv_writes_header_even_when_empty(tmp_path):
    output_path = tmp_path / "fund_flow.csv"
    export_fund_flow_csv([], output_path)

    with open(output_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == FUND_FLOW_CSV_COLUMNS
        rows = list(reader)
    assert rows == []


def test_export_transactions_csv_overwrites_existing_file(tmp_path):
    output_path = tmp_path / "transactions.csv"
    export_transactions_csv([_sample_transaction()], output_path)
    # Export again with different (empty) data -- should replace, not append.
    export_transactions_csv([], output_path)

    with open(output_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert rows == []
