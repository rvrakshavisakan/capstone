"""
csv_exporter.py

Exports processed transactions and traced fund-flow paths to CSV files.
This is the PRIMARY output of Member 1's module -- Member 2 (analytics)
and Member 3 (dashboard) consume these files directly.

Uses the standard library `csv` module (no pandas dependency required
for writing, keeping this module lightweight and easy to explain).
"""

from __future__ import annotations

import csv
from pathlib import Path

from crypto_fraud_tracker.app.transaction_processor import ProcessedTransaction
from crypto_fraud_tracker.app.transaction_tracer import FundFlowEdge

TRANSACTIONS_CSV_COLUMNS = [
    "transaction_id",
    "from_address",
    "to_address",
    "value_eth",
    "timestamp",
    #"block_number",
    #"gas",
    #"gas_price",
    #"direction",
]

FUND_FLOW_CSV_COLUMNS = [
    "source_wallet",
    "destination_wallet",
    "amount_eth",
    "hop",
    "transaction_id",
    "timestamp",
]


def _ensure_parent_dir(path: Path) -> None:
    """Create the parent directory of `path` if it does not already exist."""
    path.parent.mkdir(parents=True, exist_ok=True)


def export_transactions_csv(
    transactions: list[ProcessedTransaction],
    output_path: str | Path = "data/transactions.csv",
) -> Path:
    """
    Write processed transactions to a CSV file.

    Args:
        transactions: list of ProcessedTransaction objects to export.
        output_path: destination path (default: data/transactions.csv).
            The parent directory is created automatically if missing.

    Returns:
        The Path the file was written to.

    Notes:
        - Always writes a header row, even if `transactions` is empty,
          so downstream tools (e.g. pandas) can still load the file and
          see the expected columns.
        - Overwrites any existing file at `output_path` intentionally
          (each run represents a fresh analysis of the reported wallet).
          The file is written atomically via a temp-file + replace so a
          crash mid-write cannot leave a corrupt/partial CSV behind.
    """
    path = Path(output_path)
    _ensure_parent_dir(path)

    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TRANSACTIONS_CSV_COLUMNS)
        writer.writeheader()
        #for tx in transactions:
        #    writer.writerow(tx.as_dict())
        for tx in transactions:
            tx_data = tx.as_dict()

            writer.writerow({
                "transaction_id": tx_data.get("transaction_id"),
                "from_address": tx_data.get("from_address"),
                "to_address": tx_data.get("to_address"),
                "value_eth": tx_data.get("value_eth"),
                "timestamp": tx_data.get("timestamp"),
    })
    tmp_path.replace(path)
    return path


def export_fund_flow_csv(
    edges: list[FundFlowEdge],
    output_path: str | Path = "data/fund_flow.csv",
) -> Path:
    """
    Write traced fund-flow edges to a CSV file.

    Args:
        edges: list of FundFlowEdge objects (from transaction_tracer's
            BFS trace) to export.
        output_path: destination path (default: data/fund_flow.csv).
            The parent directory is created automatically if missing.

    Returns:
        The Path the file was written to.

    Notes:
        - Always writes a header row, even if `edges` is empty.
        - Only real, API-retrieved transactions should ever be passed
          in here; this function performs no synthesis of data.
    """
    path = Path(output_path)
    _ensure_parent_dir(path)

    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FUND_FLOW_CSV_COLUMNS)
        writer.writeheader()
        for edge in edges:
            writer.writerow(
                {
                    "source_wallet": edge.source_wallet,
                    "destination_wallet": edge.destination_wallet,
                    "amount_eth": edge.amount_eth,
                    "hop": edge.hop,
                    "transaction_id": edge.transaction_id,
                    "timestamp": edge.timestamp,
                }
            )

    tmp_path.replace(path)
    return path

