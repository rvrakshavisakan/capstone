"""
crypto_fraud_tracker.app

Member 1 module: Blockchain Data Collection and Transaction Analysis.

This package retrieves publicly available Ethereum transaction data for a
victim-reported ("suspect") wallet address, processes it into a clean
tabular form, traces connected wallets for a limited number of hops, and
exports the results as CSV files, a NetworkX graph, and an optional SQLite
cache.

This package intentionally does NOT implement fraud detection, risk
scoring, or exchange identification. Those are the responsibilities of
Member 2 (analytics) and Member 3 (dashboard).
"""

__version__ = "1.0.0"
