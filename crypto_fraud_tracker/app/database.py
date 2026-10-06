"""
database.py

Optional local SQLite storage/cache for processed transactions.

The CSV files produced by csv_exporter.py remain the PRIMARY output of
Member 1's module. This SQLite database exists only for:
    - local caching (avoid re-processing the same data repeatedly), and
    - potential future integration (e.g. Member 2/3 querying via SQL
      instead of re-reading CSVs).

No fraud detection, scoring, or classification logic lives here -- this
module only stores and retrieves plain transaction records.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from crypto_fraud_tracker.app.transaction_processor import ProcessedTransaction

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_hash TEXT NOT NULL UNIQUE,
    from_address TEXT NOT NULL,
    to_address TEXT NOT NULL,
    value_eth REAL NOT NULL,
    timestamp TEXT NOT NULL,
    block_number INTEGER NOT NULL,
    gas INTEGER NOT NULL,
    gas_price INTEGER NOT NULL,
    direction TEXT NOT NULL
);
"""

_INSERT_SQL = """
INSERT OR IGNORE INTO transactions (
    transaction_hash, from_address, to_address, value_eth,
    timestamp, block_number, gas, gas_price, direction
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
"""

_SELECT_ALL_SQL = """
SELECT id, transaction_hash, from_address, to_address, value_eth,
       timestamp, block_number, gas, gas_price, direction
FROM transactions
ORDER BY block_number ASC;
"""


def init_database(db_path: str | Path = "data/transactions.db") -> Path:
    """
    Initialise the SQLite database and create the `transactions` table
    if it does not already exist.

    Args:
        db_path: path to the SQLite database file. Parent directory is
            created automatically if missing.

    Returns:
        The Path to the initialised database file.
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as conn:
        conn.execute(_CREATE_TABLE_SQL)
        conn.commit()

    return path


def insert_transactions(
    transactions: list[ProcessedTransaction],
    db_path: str | Path = "data/transactions.db",
) -> int:
    """
    Insert processed transactions into the SQLite database.

    Duplicate transaction hashes are silently ignored (INSERT OR IGNORE),
    so this function is safe to call multiple times with overlapping data.

    Args:
        transactions: list of ProcessedTransaction objects to store.
        db_path: path to the SQLite database file.

    Returns:
        The number of NEW rows actually inserted (duplicates excluded).
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    inserted = 0
    with sqlite3.connect(path) as conn:
        conn.execute(_CREATE_TABLE_SQL)
        for tx in transactions:
            cursor = conn.execute(
                _INSERT_SQL,
                (
                    tx.transaction_id,
                    tx.from_address,
                    tx.to_address,
                    tx.value_eth,
                    tx.timestamp,
                    tx.block_number,
                    tx.gas,
                    tx.gas_price,
                    tx.direction,
                ),
            )
            if cursor.rowcount:
                inserted += 1
        conn.commit()

    return inserted


def get_all_transactions(
    db_path: str | Path = "data/transactions.db",
) -> list[dict[str, object]]:
    """
    Retrieve all transactions currently stored in the SQLite database.

    Args:
        db_path: path to the SQLite database file.

    Returns:
        A list of dictionaries, one per stored transaction, ordered by
        block number ascending. Returns an empty list if the database or
        table does not yet exist.
    """
    path = Path(db_path)
    if not path.exists():
        return []

    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(_SELECT_ALL_SQL).fetchall()
        except sqlite3.OperationalError:
            # Table doesn't exist yet.
            return []

    return [dict(row) for row in rows]
