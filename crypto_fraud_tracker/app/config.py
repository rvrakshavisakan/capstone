"""
config.py

Centralised configuration for Member 1's module.

Responsible for loading environment variables (such as the Etherscan API
key) from a local .env file using python-dotenv. No other module should
read environment variables directly -- they should import values from
here instead. This keeps secret-handling in exactly one place.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load variables from a .env file in the project root, if present.
# This does NOT create or overwrite the .env file; it only reads it.
load_dotenv()


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    """Immutable application settings loaded from environment variables."""

    etherscan_api_key: str
    etherscan_base_url: str = "https://api.etherscan.io/v2/api"
    request_timeout_seconds: int = 15
    max_retries: int = 3
    retry_backoff_seconds: float = 1.5

    # Tracing defaults (kept small deliberately for a student project /
    # limited free-tier API usage).
    default_max_hops: int = 3
    default_max_wallets: int = 25
    default_max_txs_per_wallet: int = 100


def get_settings() -> Settings:
    """
    Build and return a Settings object from environment variables.

    Returns:
        Settings: populated configuration object.

    Raises:
        ConfigError: if the ETHERSCAN_API_KEY environment variable is not
            set. The API key must NEVER be hard-coded in source code.
    """
    api_key = os.getenv("ETHERSCAN_API_KEY", "").strip()

    if not api_key or api_key == "your_api_key_here":
        raise ConfigError(
            "ETHERSCAN_API_KEY is not set. Create a .env file (see "
            ".env.example) and set ETHERSCAN_API_KEY=<your_real_key>."
        )

    return Settings(etherscan_api_key=api_key)
