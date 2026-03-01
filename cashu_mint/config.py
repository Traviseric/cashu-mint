"""Mint configuration via environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 3338
    debug: bool = False

    # Mint identity
    mint_name: str = "Cashu Mint"
    mint_description: str = "A Cashu ecash mint"
    mint_description_long: str = ""
    mint_motd: str = ""
    mint_url: str = "http://localhost:3338"

    # Database
    database_url: str = "sqlite+aiosqlite:///./cashu_mint.db"

    # Cryptography
    mint_private_key: str = ""  # Set via env; generated on first start if empty

    # Lightning backend
    lightning_backend: str = "fake"  # fake | lnd | cln | lnbits

    # LND settings
    lnd_grpc_host: str = "localhost:10009"
    lnd_tls_cert_path: str = ""
    lnd_macaroon_path: str = ""

    # CLN settings
    cln_grpc_host: str = "localhost:9736"
    cln_ca_cert_path: str = ""
    cln_client_cert_path: str = ""
    cln_client_key_path: str = ""

    # LNbits settings
    lnbits_url: str = ""
    lnbits_api_key: str = ""

    # Limits
    max_mint_amount: int = 1_000_000  # sats
    max_melt_amount: int = 1_000_000  # sats
    max_balance: int = 0  # 0 = unlimited

    # Quote expiry (seconds)
    mint_quote_ttl: int = 3600
    melt_quote_ttl: int = 3600

    # Fees
    fee_percent: float = 0.0
    fee_min: int = 0


settings = Settings()
