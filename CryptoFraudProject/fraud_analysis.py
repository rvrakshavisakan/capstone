import pandas as pd
from collections import defaultdict


# ============================================================
# CONFIGURATION
# ============================================================

TRANSACTION_FILE = "data/transactions.csv"
FLAGGED_FILE = "flagged_wallets.csv"
EXCHANGE_FILE = "exchange_wallets.csv"

HOP_LIMIT = 3
RAPID_LIMIT = 60                 # seconds
SPLIT_AMOUNT_LIMIT = 50          # ETH
SPLIT_WALLET_LIMIT = 3

BASE_RISK_POINTS = {
    "multiple_hop": 3,
    "rapid_transfer": 2,
    "fund_splitting": 3,
    "flagged_wallet": 5,
    "exchange_interaction": 2
}

BEHAVIOR_DECAY = 0.85

SEQUENCE_BONUS = {
    ("multiple_hop", "rapid_transfer"): 2,
    ("fund_splitting", "rapid_transfer"): 2,
    ("flagged_wallet", "multiple_hop"): 2,
    ("multiple_hop", "exchange_interaction"): 2
}

# Behavioral deviation thresholds
FREQUENCY_THRESHOLD = 3
LARGE_AMOUNT_THRESHOLD = 100
FLOW_RATIO_THRESHOLD = 0.70


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def add_behavior(
    wallet,
    behavior,
    suspicious_wallets,
    wallet_risk,
    behavior_counts
):
    """
    Add a suspicious wallet and record both:
    1. Unique behavior types
    2. Number of behavior occurrences
    """

    suspicious_wallets.add(wallet)

    if wallet not in wallet_risk:
        wallet_risk[wallet] = []

    if behavior not in wallet_risk[wallet]:
        wallet_risk[wallet].append(behavior)

    behavior_counts[wallet][behavior] += 1


def calculate_risk_level(score):

    if score >= 10:
        return "CRITICAL"

    elif score >= 5:
        return "HIGH"

    elif score >= 3:
        return "MEDIUM"

    else:
        return "LOW"


# ============================================================
# READ TRANSACTION DATA
# ============================================================

df = pd.read_csv(
    TRANSACTION_FILE
)

required_columns = {
    "transaction_id",
    "from_wallet",
    "to_wallet",
    "amount_eth",
    "timestamp"
}

missing_columns = (
    required_columns -
    set(df.columns)
)

if missing_columns:

    raise ValueError(
        f"Missing required columns: "
        f"{sorted(missing_columns)}"
    )


df["timestamp"] = pd.to_datetime(
    df["timestamp"]
)

df["amount_eth"] = pd.to_numeric(
    df["amount_eth"],
    errors="coerce"
)


df = df.dropna(
    subset=[
        "transaction_id",
        "from_wallet",
        "to_wallet",
        "amount_eth",
        "timestamp"
    ]
)


# Sort chronologically
df = df.sort_values(
    "timestamp"
).reset_index(drop=True)


# ============================================================
# INITIALIZE STORAGE
# ============================================================

suspicious_wallets = set()

wallet_risk = {}

# Stores actual number of occurrences
behavior_counts = defaultdict(
    lambda: defaultdict(int)
)

suspicious_paths = []


# ============================================================
# 1. MULTIPLE-HOP DETECTION
# ============================================================

print(
    "\n--- MULTIPLE HOP DETECTION ---"
)


# Map wallet -> outgoing transaction indexes
outgoing_transactions = defaultdict(list)


for i in range(len(df)):

    sender = df.loc[
        i,
        "from_wallet"
    ]

    outgoing_transactions[
        sender
    ].append(i)


for start_index in range(len(df)):

    start_from = df.loc[
        start_index,
        "from_wallet"
    ]

    start_to = df.loc[
        start_index,
        "to_wallet"
    ]

    path = [
        start_from,
        start_to
    ]

    current_wallet = start_to

    current_index = start_index

    hop_count = 1

    visited_wallets = set(path)


    while hop_count < 10:

        possible_transactions = (
            outgoing_transactions.get(
                current_wallet,
                []
            )
        )

        next_index = None


        for candidate_index in possible_transactions:

            if candidate_index <= current_index:
                continue

            candidate_to = df.loc[
                candidate_index,
                "to_wallet"
            ]

            # Prevent loops
            if candidate_to in visited_wallets:
                continue

            next_index = candidate_index

            break


        if next_index is None:
            break


        current_wallet = df.loc[
            next_index,
            "to_wallet"
        ]

        path.append(
            current_wallet
        )

        visited_wallets.add(
            current_wallet
        )

        current_index = next_index

        hop_count += 1


    if hop_count >= HOP_LIMIT:

        suspicious_paths.append(
            path
        )


        for wallet in path:

            add_behavior(
                wallet,
                "multiple_hop",
                suspicious_wallets,
                wallet_risk,
                behavior_counts
            )


if suspicious_paths:

    for path in suspicious_paths:

        print(
            "Suspicious path:",
            " → ".join(path)
        )

        print(
            "Number of hops:",
            len(path) - 1
        )

else:

    print(
        "No multiple-hop transactions detected."
    )


# ============================================================
# 2. RAPID TRANSFER DETECTION
# ============================================================

print(
    "\n--- RAPID TRANSFER DETECTION ---"
)


for i in range(len(df) - 1):

    current_to = df.loc[
        i,
        "to_wallet"
    ]

    next_from = df.loc[
        i + 1,
        "from_wallet"
    ]


    if current_to != next_from:
        continue


    time_difference = (
        df.loc[
            i + 1,
            "timestamp"
        ]
        -
        df.loc[
            i,
            "timestamp"
        ]
    ).total_seconds()


    if 0 <= time_difference <= RAPID_LIMIT:

        next_wallet = df.loc[
            i + 1,
            "to_wallet"
        ]


        add_behavior(
            current_to,
            "rapid_transfer",
            suspicious_wallets,
            wallet_risk,
            behavior_counts
        )


        add_behavior(
            next_wallet,
            "rapid_transfer",
            suspicious_wallets,
            wallet_risk,
            behavior_counts
        )


        print(
            f"Rapid transfer detected: "
            f"{current_to} → {next_wallet} "
            f"after {time_difference} seconds"
        )


# ============================================================
# 3. FUND SPLITTING DETECTION
# ============================================================

print(
    "\n--- FUND SPLITTING DETECTION ---"
)


for wallet in df[
    "to_wallet"
].unique():

    incoming_transactions = df[
        df["to_wallet"] == wallet
    ]


    incoming_amount = (
        incoming_transactions[
            "amount_eth"
        ].sum()
    )


    if incoming_amount < SPLIT_AMOUNT_LIMIT:
        continue


    outgoing = df[
        df["from_wallet"] == wallet
    ]


    different_wallets = (
        outgoing[
            "to_wallet"
        ].nunique()
    )


    if different_wallets >= SPLIT_WALLET_LIMIT:

        add_behavior(
            wallet,
            "fund_splitting",
            suspicious_wallets,
            wallet_risk,
            behavior_counts
        )


        print(
            f"Fund splitting detected: "
            f"{wallet} received "
            f"{incoming_amount} ETH and sent money to "
            f"{different_wallets} wallets"
        )


# ============================================================
# 4. FLAGGED WALLET DETECTION
# ============================================================

flagged_df = pd.read_csv(
    FLAGGED_FILE
)


if "wallet_address" not in flagged_df.columns:

    raise ValueError(
        "flagged_wallets.csv must contain "
        "'wallet_address' column."
    )


flagged_wallets = set(
    flagged_df["wallet_address"]
)


print(
    "\n--- FLAGGED WALLET DETECTION ---"
)


for i in range(len(df)):

    from_wallet = df.loc[
        i,
        "from_wallet"
    ]

    to_wallet = df.loc[
        i,
        "to_wallet"
    ]


    if from_wallet in flagged_wallets:

        add_behavior(
            from_wallet,
            "flagged_wallet",
            suspicious_wallets,
            wallet_risk,
            behavior_counts
        )


        print(
            f"Flagged wallet detected: "
            f"{from_wallet} → {to_wallet}"
        )


    if to_wallet in flagged_wallets:

        add_behavior(
            to_wallet,
            "flagged_wallet",
            suspicious_wallets,
            wallet_risk,
            behavior_counts
        )


        print(
            f"Flagged wallet detected: "
            f"{from_wallet} → {to_wallet}"
        )


# ============================================================
# 5. EXCHANGE WALLET DETECTION
# ============================================================

exchange_df = pd.read_csv(
    EXCHANGE_FILE
)


if not {
    "wallet_address",
    "exchange_name"
}.issubset(
    exchange_df.columns
):

    raise ValueError(
        "exchange_wallets.csv must contain "
        "'wallet_address' and 'exchange_name' columns."
    )


exchange_wallets = dict(
    zip(
        exchange_df["wallet_address"],
        exchange_df["exchange_name"]
    )
)


print(
    "\n--- EXCHANGE WALLET DETECTION ---"
)


for i in range(len(df)):

    from_wallet = df.loc[
        i,
        "from_wallet"
    ]

    to_wallet = df.loc[
        i,
        "to_wallet"
    ]


    # --------------------------------------------------------
    # Exchange is the sender
    # --------------------------------------------------------

    if from_wallet in exchange_wallets:

        exchange_name = exchange_wallets[
            from_wallet
        ]


        print(
            f"Exchange detected: "
            f"{from_wallet} "
            f"({exchange_name}) → {to_wallet}"
        )


    # --------------------------------------------------------
    # Exchange is the receiver
    # --------------------------------------------------------

    if to_wallet in exchange_wallets:

        exchange_name = exchange_wallets[
            to_wallet
        ]


        print(
            f"Exchange detected: "
            f"{from_wallet} → "
            f"{to_wallet} "
            f"({exchange_name})"
        )


# Known exchanges are contextual entities.
# They should not themselves appear in the
# suspicious-wallet risk ranking.

suspicious_wallets.difference_update(
    exchange_wallets.keys()
)


# ============================================================
# 6. SUSPICIOUS WALLET LIST
# ============================================================

print(
    "\n--- SUSPICIOUS WALLETS ---"
)


for wallet in sorted(
    suspicious_wallets
):

    print(wallet)


print(
    "Total suspicious wallets:",
    len(suspicious_wallets)
)


# ============================================================
# 7. WALLET BEHAVIORS
# ============================================================

print(
    "\n--- WALLET BEHAVIORS ---"
)


for wallet in sorted(
    suspicious_wallets
):

    print(
        f"{wallet}: "
        f"{wallet_risk.get(wallet, [])}"
    )


# ============================================================
# 8. ADAPTIVE RISK SCORE
# ============================================================

print(
    "\n--- ADAPTIVE RISK SCORES ---"
)


risk_results = {}


for wallet in suspicious_wallets:

    behaviors = wallet_risk.get(
        wallet,
        []
    )


    # Get actual behavior occurrence counts
    wallet_behavior_counts = (
        behavior_counts.get(
            wallet,
            {}
        )
    )


    risk_score = 0.0


    # --------------------------------------------------------
    # Repeated behavior with temporal decay
    # --------------------------------------------------------

    for behavior, count in (
        wallet_behavior_counts.items()
    ):

        base_score = BASE_RISK_POINTS.get(
            behavior,
            0
        )


        for occurrence in range(count):

            adaptive_score = (
                base_score *
                (
                    BEHAVIOR_DECAY **
                    occurrence
                )
            )


            risk_score += adaptive_score


    # --------------------------------------------------------
    # Behavior combination bonus
    # --------------------------------------------------------

    unique_behaviors = set(
        behaviors
    )


    for behavior_pair, bonus in (
        SEQUENCE_BONUS.items()
    ):

        if (
            behavior_pair[0]
            in unique_behaviors
            and
            behavior_pair[1]
            in unique_behaviors
        ):

            risk_score += bonus


    risk_score = round(
        risk_score,
        2
    )


    risk_level = calculate_risk_level(
        risk_score
    )


    risk_results[wallet] = {

        "risk_score":
            risk_score,

        "risk_level":
            risk_level,

        "behaviors":
            unique_behaviors,

        "deviation_score":
            0,

        "deviation_reasons":
            []
    }


    print(
        f"{wallet} | "
        f"Score: {risk_score} | "
        f"Risk: {risk_level} | "
        f"Behaviors: "
        f"{', '.join(sorted(unique_behaviors))}"
    )


# ============================================================
# 9. BEHAVIORAL DEVIATION ANALYSIS
# ============================================================

print(
    "\n--- BEHAVIORAL DEVIATION ANALYSIS ---"
)


wallet_transaction_stats = {}


for wallet in set(
    df["from_wallet"]
).union(
    set(df["to_wallet"])
):

    outgoing = df[
        df["from_wallet"] == wallet
    ]


    incoming = df[
        df["to_wallet"] == wallet
    ]


    transaction_count = (
        len(outgoing) +
        len(incoming)
    )


    average_amount = 0.0


    if transaction_count > 0:

        total_amount = (
            outgoing["amount_eth"].sum()
            +
            incoming["amount_eth"].sum()
        )


        average_amount = (
            total_amount /
            transaction_count
        )


    incoming_amount = incoming[
        "amount_eth"
    ].sum()


    outgoing_amount = outgoing[
        "amount_eth"
    ].sum()


    total_flow = (
        incoming_amount +
        outgoing_amount
    )


    if total_flow > 0:

        flow_ratio = (
            max(
                incoming_amount,
                outgoing_amount
            )
            /
            total_flow
        )

    else:

        flow_ratio = 0.0


    wallet_transaction_stats[
        wallet
    ] = {

        "transaction_count":
            transaction_count,

        "average_amount":
            average_amount,

        "incoming_amount":
            incoming_amount,

        "outgoing_amount":
            outgoing_amount,

        "flow_ratio":
            flow_ratio
    }


for wallet in sorted(
    suspicious_wallets
):

    stats = wallet_transaction_stats.get(
        wallet,
        {
            "transaction_count": 0,
            "average_amount": 0,
            "flow_ratio": 0
        }
    )


    transaction_count = stats[
        "transaction_count"
    ]


    average_amount = stats[
        "average_amount"
    ]


    flow_ratio = stats[
        "flow_ratio"
    ]


    deviation_score = 0

    deviation_reasons = []


    # --------------------------------------------------------
    # High transaction frequency
    # --------------------------------------------------------

    if (
        transaction_count
        >= FREQUENCY_THRESHOLD
    ):

        deviation_score += 2

        deviation_reasons.append(
            "high_transaction_frequency"
        )


    # --------------------------------------------------------
    # Unusually large transaction size
    # --------------------------------------------------------

    if (
        average_amount
        >= LARGE_AMOUNT_THRESHOLD
    ):

        deviation_score += 2

        deviation_reasons.append(
            "unusually_large_transactions"
        )


    # --------------------------------------------------------
    # High fund-flow concentration
    # --------------------------------------------------------

    if (
        flow_ratio
        >= FLOW_RATIO_THRESHOLD
    ):

        deviation_score += 2

        deviation_reasons.append(
            "high_fund_flow_ratio"
        )


    # --------------------------------------------------------
    # Update adaptive risk score
    # --------------------------------------------------------

    old_score = risk_results[
        wallet
    ]["risk_score"]


    new_score = round(
        old_score +
        deviation_score,
        2
    )


    new_level = calculate_risk_level(
        new_score
    )


    risk_results[
        wallet
    ]["risk_score"] = new_score


    risk_results[
        wallet
    ]["risk_level"] = new_level


    risk_results[
        wallet
    ]["deviation_score"] = (
        deviation_score
    )


    risk_results[
        wallet
    ]["deviation_reasons"] = (
        deviation_reasons
    )


    reasons_text = (
        ", ".join(
            deviation_reasons
        )
        if deviation_reasons
        else "None"
    )


    print(
        f"{wallet} | "
        f"Deviation: {deviation_score} | "
        f"Reasons: {reasons_text} | "
        f"Updated Score: {new_score} | "
        f"Risk: {new_level}"
    )


# ============================================================
# 10. FINAL WALLET RANKING
# ============================================================

wallet_ranking = []


for wallet in suspicious_wallets:

    result = risk_results[
        wallet
    ]


    wallet_ranking.append({

        "wallet_address":
            wallet,

        "risk_score":
            result["risk_score"],

        "risk_level":
            result["risk_level"],

        "deviation_score":
            result["deviation_score"],

        "deviation_reasons":
            ", ".join(
                result[
                    "deviation_reasons"
                ]
            )
            if result[
                "deviation_reasons"
            ]
            else "None",

        "behaviors":
            ", ".join(
                sorted(
                    result[
                        "behaviors"
                    ]
                )
            )
    })


wallet_ranking.sort(
    key=lambda x: (
        x["risk_score"],
        x["deviation_score"]
    ),
    reverse=True
)


print(
    "\n--- WALLET RANKING ---"
)


for rank, wallet in enumerate(
    wallet_ranking,
    start=1
):

    print(
        f"Rank {rank}: "
        f"{wallet['wallet_address']} | "
        f"Score: {wallet['risk_score']} | "
        f"Risk: {wallet['risk_level']} | "
        f"Deviation: {wallet['deviation_score']} | "
        f"Behaviors: {wallet['behaviors']}"
    )


# ============================================================
# 11. FRAUD REPORT
# ============================================================

report_df = pd.DataFrame(
    wallet_ranking
)


report_df.to_csv(
    "fraud_report.csv",
    index=False
)


print(
    "\n--- FRAUD REPORT CREATED ---"
)


print(
    "Report saved as: fraud_report.csv"
)


# ============================================================
# 12. EVIDENCE-BASED SUSPICIOUS TRANSACTION REPORT
# ============================================================

print(
    "\n--- EVIDENCE-BASED TRANSACTION RISK ANALYSIS ---"
)


suspicious_transactions = []


for i in range(len(df)):

    from_wallet = df.loc[
        i,
        "from_wallet"
    ]

    to_wallet = df.loc[
        i,
        "to_wallet"
    ]


    # Ignore transactions involving no suspicious wallet
    if (
        from_wallet not in suspicious_wallets
        and
        to_wallet not in suspicious_wallets
    ):

        continue


    from_result = risk_results.get(
        from_wallet,
        {
            "risk_score": 0,
            "risk_level": "LOW",
            "behaviors": set()
        }
    )


    to_result = risk_results.get(
        to_wallet,
        {
            "risk_score": 0,
            "risk_level": "LOW",
            "behaviors": set()
        }
    )


    # Select the wallet with the higher risk
    if (
        from_result["risk_score"]
        >=
        to_result["risk_score"]
    ):

        primary_wallet = from_wallet

        primary_result = from_result

    else:

        primary_wallet = to_wallet

        primary_result = to_result


    risk_score = primary_result[
        "risk_score"
    ]


    behaviors = set(
        primary_result.get(
            "behaviors",
            set()
        )
    )


    evidence = []


    # --------------------------------------------------------
    # Evidence from suspicious behaviors
    # --------------------------------------------------------

    if "multiple_hop" in behaviors:

        evidence.append(
            "multi-hop fund movement"
        )


    if "rapid_transfer" in behaviors:

        evidence.append(
            "rapid fund movement"
        )


    if "fund_splitting" in behaviors:

        evidence.append(
            "fund splitting"
        )


    if "flagged_wallet" in behaviors:

        evidence.append(
            "interaction with flagged wallet"
        )


    # --------------------------------------------------------
    # Exchange identification
    # --------------------------------------------------------

    exchange_name = "None"


    if to_wallet in exchange_wallets:

        exchange_name = exchange_wallets[
            to_wallet
        ]


        evidence.append(
            f"destination is known exchange "
            f"({exchange_name})"
        )


    elif from_wallet in exchange_wallets:

        exchange_name = exchange_wallets[
            from_wallet
        ]


        evidence.append(
            f"source is known exchange "
            f"({exchange_name})"
        )


    # --------------------------------------------------------
    # Risk level
    # --------------------------------------------------------

    risk_level = calculate_risk_level(
        risk_score
    )


    suspicious_transactions.append({

        "transaction_id":
            df.loc[
                i,
                "transaction_id"
            ],

        "from_wallet":
            from_wallet,

        "to_wallet":
            to_wallet,

        "amount_eth":
            df.loc[
                i,
                "amount_eth"
            ],

        "timestamp":
            df.loc[
                i,
                "timestamp"
            ],

        "primary_risk_wallet":
            primary_wallet,

        "adaptive_risk_score":
            risk_score,

        "risk_level":
            risk_level,

        "detected_behaviors":
            ", ".join(
                sorted(
                    behaviors
                )
            )
            if behaviors
            else "None",

        "evidence":
            "; ".join(
                evidence
            )
            if evidence
            else "No specific evidence",

        "exchange":
            exchange_name
    })


    print(
        f"{df.loc[i, 'transaction_id']} | "
        f"Risk: {risk_level} | "
        f"Score: {risk_score} | "
        f"Evidence: "
        f"{'; '.join(evidence) if evidence else 'None'}"
    )


suspicious_transactions_df = pd.DataFrame(
    suspicious_transactions
)


suspicious_transactions_df.to_csv(
    "suspicious_transactions.csv",
    index=False
)


print(
    "\n--- EVIDENCE-BASED REPORT CREATED ---"
)


print(
    "Report saved as: "
    "suspicious_transactions.csv"
)


# ============================================================
# 13. FRAUD SUMMARY
# ============================================================

print(
    "\n===================================================="
)


print(
    "                 FRAUD SUMMARY"
)


print(
    "===================================================="
)


total_transactions = len(df)


total_suspicious_transactions = len(
    suspicious_transactions_df
)


total_suspicious_wallets = len(
    suspicious_wallets
)


critical_count = 0
high_count = 0
medium_count = 0
low_count = 0


for wallet in suspicious_wallets:

    risk_score = risk_results[
        wallet
    ]["risk_score"]


    if risk_score >= 10:

        critical_count += 1

    elif risk_score >= 5:

        high_count += 1

    elif risk_score >= 3:

        medium_count += 1

    else:

        low_count += 1


print(
    f"Total transactions analyzed    : "
    f"{total_transactions}"
)


print(
    f"Suspicious transactions        : "
    f"{total_suspicious_transactions}"
)


print(
    f"Suspicious wallets             : "
    f"{total_suspicious_wallets}"
)


print(
    f"Critical-risk wallets          : "
    f"{critical_count}"
)


print(
    f"High-risk wallets              : "
    f"{high_count}"
)


print(
    f"Medium-risk wallets            : "
    f"{medium_count}"
)


print(
    f"Low-risk wallets               : "
    f"{low_count}"
)


print(
    "===================================================="
)