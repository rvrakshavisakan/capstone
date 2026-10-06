"""
main.py

Command-line entry point for Member 1's module:
Blockchain Data Collection and Transaction Analysis.

Pipeline:
    1. Validate the victim-reported wallet address.
    2. Load the Etherscan API key from .env.
    3. Retrieve the wallet's transactions from Etherscan.
    4. Process (clean/normalise) the transactions.
    5. Save transactions to SQLite (local cache).
    6. Export transactions.csv.
    7. Trace outgoing fund flow using BFS (up to N hops).
    8. Export fund_flow.csv.
    9. Build a transaction graph with NetworkX.
   10. Export transaction_graph.graphml (and .json).
   11. Print a plain-text summary.

This script performs NO fraud detection, risk scoring, or exchange
identification -- it only collects and organises publicly available
blockchain data for Member 2 and Member 3 to build on.
"""

from __future__ import annotations

import sys


from crypto_fraud_tracker.app.config import ConfigError, get_settings
from crypto_fraud_tracker.app.csv_exporter import (
    export_fund_flow_csv,
    export_transactions_csv,
)
from crypto_fraud_tracker.app.database import init_database, insert_transactions
from crypto_fraud_tracker.app.etherscan_client import (
    EtherscanClient,
    EtherscanError,
)
from crypto_fraud_tracker.app.graph_builder import (
    add_fund_flow_edges,
    build_graph_from_transactions,
    export_graphml,
    export_json,
)
from crypto_fraud_tracker.app.transaction_processor import (
    ProcessedTransaction,
    process_transactions,
)
from crypto_fraud_tracker.app.transaction_tracer import trace_fund_flow
from crypto_fraud_tracker.app.validator import validate_wallet_address
DIVIDER = "=" * 40


def _prompt_wallet_address() -> str:
    """Prompt the user for a wallet address on the terminal."""
    return input("Enter Ethereum wallet address: ").strip()


def _prompt_max_hops(default: int) -> int:
    """Prompt the user for the maximum number of tracing hops."""
    raw = input(f"Enter maximum hops (default {default}): ").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        print(f"Invalid number, using default of {default}.")
        return default
    if value < 1:
        print(f"Hops must be at least 1, using default of {default}.")
        return default
    return value


def make_wallet_fetcher(client: EtherscanClient, wallet_for_direction: str = ""):
    """
    Build a fetch function suitable for transaction_tracer.trace_fund_flow.

    Direction ("incoming"/"outgoing") is computed relative to whichever
    wallet is CURRENTLY being queried during BFS (each hop's wallet is
    its own frame of reference for "outgoing"), not the original suspect
    wallet -- this is what lets the tracer follow the money onward at
    every hop.
    """

    def fetch(wallet_address: str) -> list[ProcessedTransaction]:
        raw = client.get_transactions(wallet_address)
        return process_transactions(raw, wallet=wallet_address)

    return fetch


def run(wallet_address: str, max_hops: int) -> int:
    """
    Execute the full Member 1 pipeline for a given wallet and hop limit.

    Returns:
        Process exit code (0 = success, 1 = failure).
    """
    # Step 1: Validate wallet.
    validation = validate_wallet_address(wallet_address)
    print(DIVIDER)
    print("BLOCKCHAIN TRANSACTION ANALYSIS")
    print(DIVIDER)
    print()
    print("Wallet:")
    print(wallet_address)
    print()
    print("Status:")
    print(validation.message)

    if not validation.is_valid:
        return 1

    normalised_wallet = validation.checksum_address or validation.address

    # Step 2: Load API key / settings.
    try:
        get_settings()
    except ConfigError as exc:
        print()
        print(f"Configuration error: {exc}")
        return 1

    client = EtherscanClient()

    # Step 3: Retrieve transactions.
    try:
        raw_transactions = client.get_transactions(normalised_wallet)
    except EtherscanError as exc:
        print()
        print(f"Failed to retrieve transactions: {exc}")
        return 1

    # Step 4: Process transactions.
    transactions = process_transactions(raw_transactions, wallet=normalised_wallet)
    incoming_count = sum(1 for tx in transactions if tx.direction == "incoming")
    outgoing_count = sum(1 for tx in transactions if tx.direction == "outgoing")

    print()
    print("Transactions retrieved:")
    print(len(transactions))
    print()
    print("Incoming transactions:")
    print(incoming_count)
    print()
    print("Outgoing transactions:")
    print(outgoing_count)

    # Step 5: Save transactions to SQLite.
    init_database("data/transactions.db")
    insert_transactions(transactions, "data/transactions.db")

    # Step 6: Export transactions.csv.
    export_transactions_csv(transactions, "data/transactions.csv")

    # Step 7: Trace outgoing fund flow using BFS.
    fetch = make_wallet_fetcher(client)
    trace_result = trace_fund_flow(
        start_wallet=normalised_wallet,
        fetch_transactions=fetch,
        max_hops=max_hops,
    )

    print()
    print("Wallets discovered:")
    print(len(trace_result.visited_wallets))
    print()
    print("Maximum hops:")
    print(max_hops)

    # Step 8: Export fund_flow.csv.
    export_fund_flow_csv(trace_result.edges, "data/fund_flow.csv")

    # Step 9: Build transaction graph.
    graph = build_graph_from_transactions(transactions)
    add_fund_flow_edges(graph, trace_result.edges)

    # Step 10: Export transaction_graph.graphml (+ optional JSON).
    export_graphml(graph, "data/transaction_graph.graphml")
    export_json(graph, "data/transaction_graph.json")

    # Step 11: Print summary.
    print()
    print("CSV OUTPUT:")
    print("\u2713 data/transactions.csv")
    print("\u2713 data/fund_flow.csv")
    print()
    print("GRAPH OUTPUT:")
    print("\u2713 data/transaction_graph.graphml")
    print()
    print("DATABASE:")
    print("\u2713 data/transactions.db")
    print()
    print(DIVIDER)
    print("ANALYSIS COMPLETE")
    print(DIVIDER)

    return 0


def main() -> None:
    """Interactive terminal entry point."""
    wallet_address = _prompt_wallet_address()
    max_hops = _prompt_max_hops(default=3)
    exit_code = run(wallet_address, max_hops)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
