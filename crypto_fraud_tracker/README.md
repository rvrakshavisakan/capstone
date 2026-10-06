# Crypto Fraud Tracker — Member 1 Module
### Blockchain Data Collection and Transaction Analysis

This repository contains **Member 1's module** for the project:

> *"Real-Time Identification of Fraud-Linked Cryptocurrency Exchanges from
> Victim-Reported Suspect Wallet Addresses through Automated Blockchain
> Analytics"*

---

## 1. What this project does

A victim reports an Ethereum wallet address they believe is connected to a
scam. This module:

1. Validates that the reported address is a well-formed Ethereum address.
2. Retrieves that wallet's **publicly available** transaction history from
   the Etherscan API.
3. Cleans and organises that data (converts units, computes direction,
   removes duplicates, sorts chronologically).
4. Traces where the funds moved next, for up to **3 hops**, using
   breadth-first search (BFS).
5. Exports everything as **CSV files** (the primary output), a **NetworkX
   graph**, and an optional **SQLite** cache.

**This module does NOT decide whether anyone is a fraudster.** It only
collects and organises data. Deciding whether a pattern looks suspicious
(Member 2) and identifying which exchange a wallet belongs to (Member 3)
are explicitly out of scope here.

---

## 2. What Member 1 is responsible for

| In scope (this repo)                         | Out of scope (Members 2 & 3)         |
|-----------------------------------------------|---------------------------------------|
| Wallet address validation                     | Fraud/risk scoring                    |
| Calling the Etherscan API                     | Exchange identification               |
| Cleaning/processing transaction data          | Frontend dashboard                    |
| Multi-hop BFS tracing of outgoing funds       | Determining real-world wallet owners  |
| CSV export (`transactions.csv`, `fund_flow.csv`) | Machine learning / classification  |
| NetworkX graph construction & export          |                                        |
| SQLite local cache                            |                                        |

---

## 3. Blockchain basics you need to know

- **Wallet address**: a public identifier (e.g. `0xAbC...123`) on the
  Ethereum blockchain. Anyone can look up its transaction history — this
  is *not* private information.
- **Transaction**: a transfer of ETH (or a contract call) from one
  address to another. Every transaction is permanently recorded on the
  blockchain and is publicly viewable.
- **Wei / ETH**: Wei is the smallest unit of Ether. `1 ETH = 10^18 Wei`.
  Etherscan returns amounts in Wei; this module converts them to ETH.
- **Block number**: transactions are grouped into blocks, added to the
  chain in order. Block number is a reliable way to sort transactions
  chronologically.
- **Hops**: if wallet A sends funds to wallet B, and B sends funds to C,
  then C is "2 hops" away from A. Tracing hops shows how funds moved
  onward after reaching the suspect wallet.

---

## 4. What the Etherscan API does

[Etherscan](https://etherscan.io) is a block explorer for Ethereum. It
also offers a free public API that lets you programmatically query:
- an address's transaction history,
- balances,
- contract information, and more.

This project only uses the `account` → `txlist` endpoint, which returns
**normal transactions** (plain ETH transfers / contract calls) for a
given address — all publicly available data.

---

## 5. Getting and configuring an API key

1. Go to <https://etherscan.io/apis> and create a free account.
2. Once logged in, go to **API Keys** in your account dashboard and
   generate a new key.
3. Copy the key — you'll paste it into your `.env` file in Step 8 below.

The free tier is sufficient for this student project (rate limits are
handled automatically by `etherscan_client.py`).

---

## 6. Create a Python virtual environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` appear at the start of your terminal prompt once
activated.

---

## 7. Install requirements

```bash
pip install -r requirements.txt
```

This installs: `requests`, `pandas`, `networkx`, `python-dotenv`, `web3`,
and `pytest`.

---

## 8. Configure your `.env` file

1. Copy the example file:
   - Windows: `copy .env.example .env`
   - macOS/Linux: `cp .env.example .env`
2. Open `.env` in a text editor and replace the placeholder with your
   real key:
   ```
   ETHERSCAN_API_KEY=your_actual_key_here
   ```
3. **Never commit your real `.env` file.** It is already listed in
   `.gitignore`.

---

## 9. Run `main.py`

```bash
python main.py
```

You will be prompted for:
```
Enter Ethereum wallet address:
Enter maximum hops (default 3):
```

Enter any valid Ethereum address you want to investigate (e.g. paste in
a wallet address a victim reported to you), and press Enter at the hops
prompt to accept the default of 3.

---

## 10. What `data/transactions.csv` contains

Every transaction directly involving the reported wallet:

| Column            | Description                                             |
|-------------------|----------------------------------------------------------|
| transaction_hash  | Unique identifier of the transaction                      |
| from_address      | Sender's wallet address                                   |
| to_address        | Recipient's wallet address                                |
| value_eth         | Amount transferred, in ETH                                 |
| timestamp         | UTC date/time the transaction was confirmed                |
| block_number      | Block the transaction was included in                      |
| gas               | Gas units used                                              |
| gas_price         | Gas price (in Wei)                                          |
| direction         | `incoming`, `outgoing`, or `self` relative to the wallet    |

---

## 11. What `data/fund_flow.csv` contains

The traced path of funds moving outward from the suspect wallet, hop by
hop (via BFS):

| Column               | Description                                          |
|----------------------|-------------------------------------------------------|
| source_wallet        | Wallet the funds moved FROM                            |
| destination_wallet    | Wallet the funds moved TO                              |
| amount_eth            | Amount transferred, in ETH                            |
| hop                   | Hop number (1 = direct from suspect wallet, 2 = next, ...) |
| transaction_hash      | The actual on-chain transaction that moved the funds    |
| timestamp             | UTC date/time of that transaction                       |

Every row corresponds to a **real, retrieved blockchain transaction** —
no data is invented.

---

## 12. What `data/transaction_graph.graphml` contains

A directed graph (`networkx.MultiDiGraph`) where:
- **nodes** = wallet addresses,
- **edges** = transactions, with attributes `amount_eth`,
  `transaction_hash`, `timestamp`, and `hop`.

GraphML can be opened in tools like [Gephi](https://gephi.org/) for
visual network analysis. A `transaction_graph.json` (node-link format)
is also produced for easy programmatic/dashboard use.

---

## 13. How Member 2 can use these CSV files

```python
import pandas as pd

transactions = pd.read_csv("data/transactions.csv")
fund_flow = pd.read_csv("data/fund_flow.csv")

# Example starting points for Member 2's own analysis:
# transactions.groupby("direction")["value_eth"].sum()
# fund_flow.sort_values("timestamp")
```

From here, Member 2 can independently build:
- suspicious pattern detection
- transaction frequency analysis
- rapid transfer ("layering") detection
- wallet behaviour analysis
- risk scoring

None of that logic exists in this repository by design.

---

## 14. Example terminal output

```
========================================
BLOCKCHAIN TRANSACTION ANALYSIS
========================================

Wallet:
0xABC123...

Status:
Valid Ethereum address

Transactions retrieved:
125

Incoming transactions:
48

Outgoing transactions:
77

Wallets discovered:
12

Maximum hops:
3

CSV OUTPUT:
✓ data/transactions.csv
✓ data/fund_flow.csv

GRAPH OUTPUT:
✓ data/transaction_graph.graphml

DATABASE:
✓ data/transactions.db

========================================
ANALYSIS COMPLETE
========================================
```

---

## 15. Legal and ethical limitations

- This tool only reads **publicly available** blockchain data (anyone
  can look up any Ethereum address's transaction history on Etherscan).
- It never accesses private keys, seed phrases, passwords, or private
  account credentials.
- It never attempts to determine the real-world identity of a wallet
  owner.
- It never labels a wallet, owner, or exchange as "fraudulent" — it uses
  neutral terms like *suspect wallet*, *reported wallet*, *transaction
  path*, and *associated address* throughout.
- Any conclusions about fraud risk must come from a human investigator
  or from Member 2/3's separate analytical components — not from this
  data-collection module.

---

## 16. Running the tests

```bash
pytest
```

All tests use mocked API responses (via `unittest.mock`) — **no real
Etherscan API key is required** to run the test suite.

---

## 17. Project structure

```
crypto_fraud_tracker/
├── app/
│   ├── __init__.py
│   ├── config.py               # Loads ETHERSCAN_API_KEY from .env
│   ├── validator.py            # Wallet address format validation
│   ├── etherscan_client.py     # Etherscan API HTTP client
│   ├── transaction_processor.py# Cleans/normalises raw transactions
│   ├── transaction_tracer.py   # BFS multi-hop fund-flow tracing
│   ├── csv_exporter.py         # Writes transactions.csv & fund_flow.csv
│   ├── graph_builder.py        # Builds & exports the NetworkX graph
│   └── database.py             # Optional SQLite cache
├── data/                       # Generated output (CSV/DB/graph files)
├── tests/                      # Pytest test suite (mocked API calls)
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
└── main.py                     # CLI entry point
```
