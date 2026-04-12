import uuid
from kiteconnect import KiteConnect

from app.services.token_manager import decrypt_token

# In-memory cache of KiteConnect instances per account
_kite_instances: dict[uuid.UUID, KiteConnect] = {}

# In-memory cache of per-account API keys
_account_api_keys: dict[uuid.UUID, str] = {}


def get_kite_client(
    account_id: uuid.UUID | None = None,
    api_key: str | None = None,
    access_token_encrypted: str | None = None,
) -> KiteConnect:
    """Get or create a KiteConnect instance for an account.

    If api_key and access_token_encrypted are provided, the instance is (re)created.
    If only account_id is provided, returns the cached instance (raises if not found).
    If api_key is provided without access_token, creates a bare client (for login URLs).
    """
    if account_id and api_key and access_token_encrypted:
        kite = KiteConnect(api_key=api_key)
        kite.set_access_token(decrypt_token(access_token_encrypted))
        _kite_instances[account_id] = kite
        _account_api_keys[account_id] = api_key
        return kite

    if account_id and api_key:
        # Bare client with API key (for login URL generation)
        kite = KiteConnect(api_key=api_key)
        _account_api_keys[account_id] = api_key
        return kite

    if account_id and account_id in _kite_instances:
        return _kite_instances[account_id]

    if account_id:
        raise ValueError(f"No KiteConnect instance for account {account_id}. Token may not be loaded.")

    raise ValueError("account_id and api_key are required")


def remove_kite_client(account_id: uuid.UUID) -> None:
    """Remove cached KiteConnect instance (e.g., on token expiry)."""
    _kite_instances.pop(account_id, None)
    _account_api_keys.pop(account_id, None)


def clear_all_clients() -> None:
    """Clear all cached instances (e.g., on daily token cleanup)."""
    _kite_instances.clear()
    _account_api_keys.clear()
