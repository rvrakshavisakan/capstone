"""
transaction_tracer.py

Multi-hop tracing of outgoing fund flow starting from a victim-reported
suspect wallet, using breadth-first search (BFS).

The tracer only follows OUTGOING transactions (suspect wallet -> next
wallet -> next wallet ...), since the goal is to see where reported funds
moved to, not to reconstruct a wallet's entire transaction graph.

This module performs no fraud/risk analysis. It only records which
addresses received funds from previously-visited addresses, how much,
and at what hop depth, based purely on real transactions returned by the
Etherscan API.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable, Iterable

from crypto_fraud_tracker.app.transaction_processor import ProcessedTransaction

# Type alias: a function that, given a wallet address, returns that
# wallet's processed transactions. In production this is backed by
# EtherscanClient + process_transactions; in tests it is a mock/fake.
TransactionFetcher = Callable[[str], Iterable[ProcessedTransaction]]


@dataclass(frozen=True)
class FundFlowEdge:
    """One traced fund-flow edge discovered during BFS tracing."""

    source_wallet: str
    destination_wallet: str
    amount_eth: float
    hop: int
    transaction_id: str
    timestamp: str


@dataclass(frozen=True)
class TraceResult:
    """The complete result of a multi-hop BFS trace."""

    edges: list[FundFlowEdge]
    visited_wallets: set[str]
    max_hops_reached: int


def trace_fund_flow(
    start_wallet: str,
    fetch_transactions: TransactionFetcher,
    max_hops: int = 3,
    max_wallets: int = 25,
) -> TraceResult:
    """
    Trace outgoing fund flow from a starting wallet using BFS, up to a
    limited number of hops and a limited total number of wallets visited.

    Args:
        start_wallet: the victim-reported suspect wallet address.
        fetch_transactions: a callable that returns processed
            transactions for a given wallet address. Injected as a
            dependency so this function can be unit-tested without any
            real network access.
        max_hops: maximum number of hops to trace outward from
            `start_wallet` (default 3, per project scope).
        max_wallets: safety cap on the total number of distinct wallets
            processed, to prevent excessive API usage on wallets with
            very wide fan-out.

    Returns:
        TraceResult containing every discovered fund-flow edge, the set
        of wallets visited, and the maximum hop depth actually reached.

    Notes:
        - A visited-wallet set prevents infinite loops and prevents the
          same wallet from being queried more than once, even if it
          appears again at a different hop.
        - Only OUTGOING transactions are followed (i.e. we trace where
          money moved FROM each visited wallet).
        - Wallets with no outgoing transactions simply contribute no
          further edges; this is not an error condition.
    """
    if max_hops < 1:
        raise ValueError("max_hops must be at least 1.")
    if max_wallets < 1:
        raise ValueError("max_wallets must be at least 1.")

    start_normalised = start_wallet.strip()

    visited: set[str] = {start_normalised.lower()}
    edges: list[FundFlowEdge] = []
    max_hop_reached = 0

    # Each queue item is (wallet_address, current_hop_depth).
    queue: deque[tuple[str, int]] = deque()
    queue.append((start_normalised, 0))

    wallets_processed = 0

    while queue:
        current_wallet, current_hop = queue.popleft()

        if current_hop >= max_hops:
            continue
        if wallets_processed >= max_wallets:
            break

        try:
            transactions = list(fetch_transactions(current_wallet))
        except Exception:
            # A failure fetching one wallet's data (e.g. transient API
            # error) should not abort the entire trace -- skip and
            # continue with wallets already queued.
            continue

        wallets_processed += 1
        next_hop = current_hop + 1

        for tx in transactions:
            if tx.direction != "outgoing":
                continue

            destination = (tx.to_address or "").strip()
            if not destination:
                continue

            edges.append(
                FundFlowEdge(
                    source_wallet=current_wallet,
                    destination_wallet=destination,
                    amount_eth=tx.value_eth,
                    hop=next_hop,
                    transaction_id=tx.transaction_id,
                    timestamp=tx.timestamp,
                )
            )
            max_hop_reached = max(max_hop_reached, next_hop)

            destination_key = destination.lower()
            if (
                destination_key not in visited
                and next_hop < max_hops
                and wallets_processed < max_wallets
            ):
                visited.add(destination_key)
                queue.append((destination, next_hop))

    return TraceResult(
        edges=edges,
        visited_wallets=visited,
        max_hops_reached=max_hop_reached,
    )

