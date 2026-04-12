import uuid
from kiteconnect import KiteConnect

from app.config import settings
from app.services.token_manager import decrypt_token

# In-memory cache of KiteConnect instances per account
_kite_instances: dict[uuid.UUID, KiteConnect] = {}


def get_kite_client(account_id: uuid.UUID | None = None, access_token_encrypted: str | None = None) -> KiteConnect:
    """Get or create a KiteConnect instance for an account.

    If access_token_encrypted is provided, the instance is (re)created with the decrypted token.
    If only account_id is provided, returns the cached instance (raises if not found).
    If neither is provided, returns a bare client (for generating login URLs).
    """
    if account_id and access_token_encrypted:
        kite = KiteConnect(api_key=settings.kite_api_key)
        kite.set_access_token(decrypt_token(access_token_encrypted))
        _kite_instances[account_id] = kite
        return kite

    if account_id and account_id in _kite_instances:
        return _kite_instances[account_id]

    if account_id:
        raise ValueError(f"No KiteConnect instance for account {account_id}. Token may not be loaded.")

    # Bare client for login URL generation
    return KiteConnect(api_key=settings.kite_api_key)


def remove_kite_client(account_id: uuid.UUID) -> None:
    """Remove cached KiteConnect instance (e.g., on token expiry)."""
    _kite_instances.pop(account_id, None)


def clear_all_clients() -> None:
    """Clear all cached instances (e.g., on daily token cleanup)."""
    _kite_instances.clear()
