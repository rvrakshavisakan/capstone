"""
graph_builder.py

Builds a directed transaction graph using NetworkX, where:
    - each wallet address is a node
    - each transaction is a directed edge (from_address -> to_address)

Edge attributes store the amount transferred, transaction hash,
timestamp, and hop number (hop is only meaningful for edges discovered
via BFS tracing; direct wallet transactions default to hop 0).

Exports the graph to GraphML (primary) and JSON (optional, for easy
inspection or use by Member 3's dashboard).
"""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
from networkx.readwrite import json_graph

from crypto_fraud_tracker.app.transaction_processor import ProcessedTransaction
from crypto_fraud_tracker.app.transaction_tracer import FundFlowEdge


def build_graph_from_transactions(
    transactions: list[ProcessedTransaction],
) -> nx.MultiDiGraph:
    """
    Build a directed multigraph from a wallet's processed transactions.

    A MultiDiGraph is used (rather than a simple DiGraph) because two
    wallets may exchange funds more than once, and each such transaction
    should remain a distinct edge rather than being collapsed/overwritten.

    Args:
        transactions: processed transactions for the investigated wallet.

    Returns:
        A networkx.MultiDiGraph with wallet addresses as nodes and
        transactions as directed edges.
    """
    graph: nx.MultiDiGraph = nx.MultiDiGraph()

    for tx in transactions:
        graph.add_node(tx.from_address)
        graph.add_node(tx.to_address)
        graph.add_edge(
            tx.from_address,
            tx.to_address,
            amount_eth=tx.value_eth,
            transaction_hash=tx.transaction_id,
            timestamp=tx.timestamp,
            hop=0,
        )

    return graph


def add_fund_flow_edges(
    graph: nx.MultiDiGraph,
    edges: list[FundFlowEdge],
) -> nx.MultiDiGraph:
    """
    Add BFS-traced fund-flow edges (potentially involving wallets beyond
    the original investigated wallet) into an existing graph.

    Args:
        graph: an existing graph (e.g. built from build_graph_from_transactions).
        edges: fund-flow edges discovered via transaction_tracer.trace_fund_flow.

    Returns:
        The same graph object, mutated in place, with the traced edges added.
    """
    for edge in edges:
        graph.add_node(edge.source_wallet)
        graph.add_node(edge.destination_wallet)
        graph.add_edge(
            edge.source_wallet,
            edge.destination_wallet,
            amount_eth=edge.amount_eth,
            transaction_hash=edge.transaction_id,
            timestamp=edge.timestamp,
            hop=edge.hop,
        )
    return graph


def export_graphml(graph: nx.MultiDiGraph, output_path: str | Path) -> Path:
    """
    Export a graph to GraphML format.

    Args:
        graph: the graph to export.
        output_path: destination file path (e.g. data/transaction_graph.graphml).

    Returns:
        The Path the file was written to.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(graph, path)
    return path


def export_json(graph: nx.MultiDiGraph, output_path: str | Path) -> Path:
    """
    Export a graph to a node-link JSON format (optional, for easy
    inspection or use by a future frontend/dashboard).

    Args:
        graph: the graph to export.
        output_path: destination file path (e.g. data/transaction_graph.json).

    Returns:
        The Path the file was written to.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json_graph.node_link_data(graph, edges="edges")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path
