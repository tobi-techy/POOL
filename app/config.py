"""POOL agent settings. Secrets come from env, never from chat."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "pool"
    # Binance Web3 API (hackathon key)
    binance_api_key: str = ""
    binance_api_secret: str = ""
    # Glider B2B
    glider_api_key: str = ""
    glider_base_url: str = "https://api.glider.fi/v2"
    # Photon sidecar (shared secret between agent and sidecar)
    sidecar_url: str = "http://127.0.0.1:8788"
    sidecar_secret: str = ""
    spectrum_webhook_secret: str = ""
    # Chat model (tonight: empty = canned replies; set to enable her voice)
    llm_api_key: str = ""
    llm_model: str = ""
    # Demo safety caps
    max_copy_usd: float = 25.0
    max_total_usd: float = 100.0
    db_path: str = "pool.db"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
