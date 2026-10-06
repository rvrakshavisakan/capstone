"""Tests for app.transaction_tracer -- BFS multi-hop fund-flow tracing."""

from app.transaction_processor import ProcessedTransaction
from app.transaction_tracer import trace_fund_flow

SUSPECT = "0xSUSPECT"
WALLET_A = "0xAAA"
WALLET_B = "0xBBB"
WALLET_C = "0xCCC"


def _tx(tx_hash, from_addr, to_addr, direction, value=1.0, block=1):
    return ProcessedTransaction(
        transaction_hash=tx_hash,
        from_address=from_addr,
        to_address=to_addr,
        value_eth=value,
        timestamp="2026-09-07 10:00:00",
        block_number=block,
        gas=21000,
        gas_price=50_000_000_000,
        direction=direction,
    )


def _make_fetcher(wallet_transactions: dict):
    """Build a fake fetch_transactions function from a dict of wallet -> txs."""

    def fetch(wallet_address):
        return wallet_transactions.get(wallet_address, [])

    return fetch


def test_bfs_traces_a_simple_chain():
    # SUSPECT -> A -> B -> C
    wallet_transactions = {
        SUSPECT: [_tx("0x1", SUSPECT, WALLET_A, "outgoing")],
        WALLET_A: [_tx("0x2", WALLET_A, WALLET_B, "outgoing")],
        WALLET_B: [_tx("0x3", WALLET_B, WALLET_C, "outgoing")],
        WALLET_C: [],
    }
    fetch = _make_fetcher(wallet_transactions)

    result = trace_fund_flow(SUSPECT, fetch, max_hops=3)

    destinations = [edge.destination_wallet for edge in result.edges]
    assert destinations == [WALLET_A, WALLET_B, WALLET_C]
    assert [edge.hop for edge in result.edges] == [1, 2, 3]
    assert result.max_hops_reached == 3


def test_bfs_respects_max_hops_limit():
    wallet_transactions = {
        SUSPECT: [_tx("0x1", SUSPECT, WALLET_A, "outgoing")],
        WALLET_A: [_tx("0x2", WALLET_A, WALLET_B, "outgoing")],
        WALLET_B: [_tx("0x3", WALLET_B, WALLET_C, "outgoing")],
    }
    fetch = _make_fetcher(wallet_transactions)

    result = trace_fund_flow(SUSPECT, fetch, max_hops=1)

    # Only the first hop (SUSPECT -> A) should be traced.
    assert len(result.edges) == 1
    assert result.edges[0].destination_wallet == WALLET_A


def test_bfs_prevents_infinite_loops_on_cycles():
    # SUSPECT -> A -> SUSPECT (a cycle)
    wallet_transactions = {
        SUSPECT: [_tx("0x1", SUSPECT, WALLET_A, "outgoing")],
        WALLET_A: [_tx("0x2", WALLET_A, SUSPECT, "outgoing")],
    }
    fetch = _make_fetcher(wallet_transactions)

    # Should terminate (not hang) even with a generous hop limit.
    result = trace_fund_flow(SUSPECT, fetch, max_hops=10)

    # SUSPECT should only ever be fetched once (it's the start wallet),
    # and the cycle back to SUSPECT should not cause re-processing.
    assert len(result.visited_wallets) == 2  # SUSPECT and A only


def test_bfs_handles_wallet_with_no_outgoing_transactions():
    wallet_transactions = {SUSPECT: []}
    fetch = _make_fetcher(wallet_transactions)

    result = trace_fund_flow(SUSPECT, fetch, max_hops=3)

    assert result.edges == []
    assert result.visited_wallets == {SUSPECT.lower()}


def test_bfs_ignores_incoming_transactions():
    wallet_transactions = {
        SUSPECT: [
            _tx("0x1", WALLET_A, SUSPECT, "incoming"),
            _tx("0x2", SUSPECT, WALLET_B, "outgoing"),
        ],
    }
    fetch = _make_fetcher(wallet_transactions)

    result = trace_fund_flow(SUSPECT, fetch, max_hops=2)

    assert len(result.edges) == 1
    assert result.edges[0].destination_wallet == WALLET_B


def test_bfs_respects_max_wallets_cap():
    # A wide fan-out: SUSPECT sends to many different wallets.
    fanout_txs = [
        _tx(f"0x{i}", SUSPECT, f"0xW{i}", "outgoing") for i in range(10)
    ]
    wallet_transactions = {SUSPECT: fanout_txs}
    fetch = _make_fetcher(wallet_transactions)

    result = trace_fund_flow(SUSPECT, fetch, max_hops=3, max_wallets=1)

    # Only the starting wallet should be processed (fetched) before the
    # cap halts further BFS expansion.
    assert len(result.edges) == 10  # all edges from the one processed wallet
    # but none of the discovered wallets should have been expanded further
    # (max_wallets=1 means only SUSPECT itself was fetched)


def test_invalid_max_hops_raises():
    import pytest

    with pytest.raises(ValueError):
        trace_fund_flow(SUSPECT, _make_fetcher({}), max_hops=0)


def test_invalid_max_wallets_raises():
    import pytest

    with pytest.raises(ValueError):
        trace_fund_flow(SUSPECT, _make_fetcher({}), max_hops=3, max_wallets=0)
