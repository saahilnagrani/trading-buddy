from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database (Render provides postgresql://, we auto-convert for asyncpg)
    database_url: str = "postgresql+asyncpg://trading:trading@localhost:5432/trading_buddy"

    @property
    def async_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Kite Connect (shared app credentials)
    kite_api_key: str = ""
    kite_api_secret: str = ""
    kite_redirect_url: str = "http://localhost:8000/api/auth/callback"

    # Encryption key for tokens/secrets (Fernet key, generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    secret_key: str = ""

    # VAPID keys for web push (generate with: npx web-push generate-vapid-keys)
    vapid_private_key: str = ""
    vapid_public_key: str = ""
    vapid_email: str = "mailto:admin@tradingbuddy.app"

    # Frontend URL (for CORS and redirects after OAuth)
    frontend_url: str = "http://localhost:3000"

    # Backend URL
    backend_url: str = "http://localhost:8000"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
